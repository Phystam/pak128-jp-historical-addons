# Encoding: utf-8
require 'rbconfig'
require 'fileutils'

class Makeobj
  def initialize
    host_os = RbConfig::CONFIG['host_os']
    @os =
      if host_os =~ /linux/
        :linux
      elsif host_os =~ /mswin|mingw|cygwin/
        :windows
      else
        raise "Unsupported OS: #{host_os}"
      end

    # Find makeobj executable
    candidates = [
      ENV['MAKEOBJ_PATH'],
      File.expand_path('../makeobj/makeobj.exe', __dir__),
      File.expand_path('../makeobj/Makeobj-Extended.exe', __dir__),
      File.expand_path('../makeobj/makeobj', __dir__),
      File.expand_path('../makeobj/makeobj-extended', __dir__),
      'makeobj'
    ].compact

    @makeobj_path = candidates.find { |p| File.exist?(p) } || 'makeobj'
    puts "Detected OS: #{@os}, using makeobj: #{@makeobj_path}"
  end

  def create_pak(dat_file, size = 128, pak_file = nil)
    pak_file ||= dat_file.sub(/\.dat$/, '.pak')
    FileUtils.mkdir_p(File.dirname(pak_file))

    # Run makeobj with working directory set to dat_file's directory so relative PNGs resolve correctly
    dat_dir = File.dirname(File.expand_path(dat_file))
    dat_base = File.basename(dat_file)
    abs_pak = File.expand_path(pak_file)

    cmd = [@makeobj_path, "pak#{size}", abs_pak, dat_base]
    IO.popen(cmd, 'r:binary', chdir: dat_dir, err: [:child, :out]) do |io|
      io.each_line do |raw_line|
        line = raw_line.encode('utf-8', 'binary', invalid: :replace, undef: :replace).chomp
        calm_prefix = [
          'Writing file ',
          '   Reading file ',
          '      packing '
        ]
        puts line if calm_prefix.all? { |pfx| !line.start_with?(pfx) }
      end
    end

    raise "makeobj failed for #{dat_file} with exit code #{$?.exitstatus}" unless $?.success?
  end

  def merge_paks(target_pak, source_paks)
    FileUtils.mkdir_p(File.dirname(target_pak))
    abs_target = File.expand_path(target_pak)
    abs_sources = source_paks.map { |p| File.expand_path(p) }

    # Remove existing target if it exists
    File.delete(abs_target) if File.exist?(abs_target)

    puts "Merging #{abs_sources.size} pak files into #{target_pak}..."
    cmd = [@makeobj_path, 'MERGE', abs_target] + abs_sources
    IO.popen(cmd, 'r:binary', err: [:child, :out]) do |io|
      io.each_line do |raw_line|
        line = raw_line.encode('utf-8', 'binary', invalid: :replace, undef: :replace).chomp
        puts line unless line.strip.empty?
      end
    end

    raise "makeobj merge failed with exit code #{$?.exitstatus}" unless $?.success?
    puts "Successfully created merged pak: #{target_pak} (#{File.size(abs_target)} bytes)"
  end
end
