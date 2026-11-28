# Encoding: utf-8
require 'rbconfig'
require 'fileutils'
require 'tmpdir'

class Makeobj
  MERGE_BATCH_SIZE = 80
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
    abs_sources = source_paks.map { |p| File.expand_path(p) }.sort

    File.delete(abs_target) if File.exist?(abs_target)

    puts "Merging #{abs_sources.size} pak files into #{target_pak}..."
    if abs_sources.size <= MERGE_BATCH_SIZE
      run_merge(abs_target, abs_sources)
    else
      merge_chunked(abs_target, abs_sources)
    end
    puts "Successfully created merged pak: #{target_pak} (#{File.size(abs_target)} bytes)"
  end

  private

  def merge_chunked(abs_target, abs_sources, depth = 0)
    if abs_sources.size <= MERGE_BATCH_SIZE
      run_merge(abs_target, abs_sources)
      return
    end

    Dir.mktmpdir("makeobj_merge_#{depth}") do |tmp_dir|
      chunk_paks = []
      abs_sources.each_slice(MERGE_BATCH_SIZE).with_index do |batch, idx|
        chunk_pak = File.join(tmp_dir, "chunk_#{depth}_#{idx}.pak")
        run_merge(chunk_pak, batch)
        chunk_paks << chunk_pak
      end
      merge_chunked(abs_target, chunk_paks, depth + 1)
    end
  end

  def run_merge(out_pak, in_paks)
    File.delete(out_pak) if File.exist?(out_pak)
    cmd = [@makeobj_path, 'MERGE', out_pak] + in_paks
    IO.popen(cmd, 'r:binary', err: [:child, :out]) do |io|
      io.each_line do |raw_line|
        line = raw_line.encode('utf-8', 'binary', invalid: :replace, undef: :replace).chomp
        puts line unless line.strip.empty?
      end
    end
    raise "makeobj merge failed with exit code #{$?.exitstatus}" unless $?.success?
  end
end
