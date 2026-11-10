#!/usr/bin/env ruby
# Encoding: utf-8

HELP_MESSAGE = <<~EOS
  ruby scripts/make.rb <command>

  COMMANDS:
    all       : スプレッドシート同期から統合pak・ja.tab生成まで一気通貫実行
    sync      : Google Spreadsheet (.gsheet / URL) からパラメータを同期
    makedat   : dattファイルからdatファイルとjatabを生成
    makeobj   : datファイルからbuild_stagingに個別pakを生成
    merge     : build_stagingのpakをマージしてbuild/yayoi_all.pakを生成
    tab       : build/text/ja.tab (およびen.tab) を生成
    clean     : 生成されたdat, jatab, staging pak, build pakを削除
    help      : このヘルプを表示
EOS

CATEGORIES = %w[
  buildings
  Industries
  ways
  way-objects
  stations
  vehicles
  citycars
  pedestrians
  crossings
  goods
  depots
]

DEFAULT_PAK_SIZE = 128

require 'fileutils'
require './scripts/makedat'
require './scripts/makeobj'
require './scripts/sync_sheets'

class Make
  def initialize
    @base_dir = Dir.pwd
    @build_staging = File.join(@base_dir, 'build_staging')
    @build_dir = File.join(@base_dir, 'build')
    @build_text_dir = File.join(@build_dir, 'text')
  end

  def run(args)
    if args.empty? || args.include?('help')
      puts HELP_MESSAGE
      return
    end

    args.each do |cmd|
      case cmd
      when 'all'
        all
      when 'sync'
        sync
      when 'makedat'
        makedat
      when 'makeobj'
        makeobj
      when 'merge'
        merge
      when 'tab', 'maketab'
        maketab
      when 'clean'
        clean
      else
        puts "Unknown command: #{cmd}"
        puts HELP_MESSAGE
        break
      end
    end
  end

  def all
    puts "=========================================================="
    puts " Starting Full Build Pipeline"
    puts "=========================================================="
    sync
    makedat
    makeobj
    merge
    maketab
    puts "=========================================================="
    puts " Full Build Pipeline Finished Successfully!"
    puts " Output package: build/JP_Historical_all.pak"
    puts " Output text   : build/text/ja.tab"
    puts "=========================================================="
  end

  def sync
    syncer = SyncSheets.new(@base_dir)
    syncer.sync_all
  end

  def master_datt?(file)
    cat_dir = CATEGORIES.map { |c| File.join(@base_dir, c) }.find { |c| file.start_with?(c) }
    return false unless cat_dir
    File.dirname(File.expand_path(file)) == File.expand_path(cat_dir)
  end

  def makedat
    puts "=== Step: Generating DAT and TAB files from DATT ==="
    makedat_tool = MakeDat.new

    CATEGORIES.each do |cat|
      cat_dir = File.join(@base_dir, cat)
      next unless Dir.exist?(cat_dir)

      Dir.glob("#{cat_dir}/**/*.datt").each do |datt_file|
        next if master_datt?(datt_file)

        dat_file = datt_file.sub(/\.datt$/, '.dat')
        jatab_file = datt_file.sub(/\.datt$/, '.jatab')
        entab_file = datt_file.sub(/\.datt$/, '.entab')

        deps = collect_dependencies(datt_file)
        dat_mtime = File.exist?(dat_file) ? File.mtime(dat_file) : Time.at(0)
        jatab_mtime = File.exist?(jatab_file) ? File.mtime(jatab_file) : Time.at(0)
        oldest_mtime = [dat_mtime, jatab_mtime].min

        # Rebuild if any dependency is newer than the output dat/jatab
        needs_rebuild = deps.any? { |dep| !File.exist?(dep) || File.mtime(dep) > oldest_mtime }
        if needs_rebuild || !File.exist?(dat_file)
          rel_datt = datt_file.sub(@base_dir + '/', '')
          puts "  makedat: #{rel_datt}"
          makedat_tool.create_dat(datt_file)
        end
      end
    end
  end

  def collect_dependencies(datt_file)
    dependencies = [datt_file]
    return dependencies unless File.exist?(datt_file)

    File.readlines(datt_file, encoding: 'utf-8').each do |line|
      case line
      when /^%require\s+['"](.*)['"]/
        req_file = File.expand_path($1, File.dirname(datt_file))
        dependencies += collect_dependencies(req_file)
      when /^%require_excel\s+['"](.*)['"]/
        req_file = File.expand_path($1, File.dirname(datt_file))
        dependencies << req_file
      when /^%require_ruby\s+['"](.*)['"]/
        req_file = File.expand_path($1, File.dirname(datt_file))
        dependencies << req_file
      end
    end
    dependencies.uniq
  end

  def makeobj
    puts "=== Step: Compiling PAK files with makeobj -> build_staging ==="
    FileUtils.mkdir_p(@build_staging)
    makeobj_tool = Makeobj.new

    CATEGORIES.each do |cat|
      cat_dir = File.join(@base_dir, cat)
      next unless Dir.exist?(cat_dir)

      Dir.glob("#{cat_dir}/**/*.dat").each do |dat_file|
        base_name = File.basename(dat_file, '.dat')
        pak_file = File.join(@build_staging, "#{base_name}.pak")

        deps = collect_dat_dependencies(dat_file)
        pak_mtime = File.exist?(pak_file) ? File.mtime(pak_file) : Time.at(0)
        needs_rebuild = deps.any? { |dep| !File.exist?(dep) || File.mtime(dep) > pak_mtime }

        if needs_rebuild || !File.exist?(pak_file)
          rel_dat = dat_file.sub(@base_dir + '/', '')
          puts "  makeobj: #{rel_dat} -> build_staging/#{base_name}.pak"
          makeobj_tool.create_pak(dat_file, DEFAULT_PAK_SIZE, pak_file)
        end
      end
    end
  end

  def collect_dat_dependencies(dat_file)
    dependencies = [dat_file]
    return dependencies unless File.exist?(dat_file)

    dat_dir = File.dirname(dat_file)
    File.readlines(dat_file, encoding: 'utf-8').each do |line|
      if line =~ /^\w+(\[[a-zA-Z0-9-]+\])*\s*=\s*(> )?([^,.]+)\.\d+\.\d+/
        img_base = $3.strip
        png_path = File.join(dat_dir, "#{img_base}.png")
        dependencies << png_path if File.exist?(png_path)
      end
    end
    dependencies.uniq
  end

  def merge
    puts "=== Step: Merging PAK files -> build/JP_Historical_all.pak ==="
    FileUtils.mkdir_p(@build_dir)
    makeobj_tool = Makeobj.new

    source_paks = Dir.glob("#{@build_staging}/*.pak").reject do |f|
      base = File.basename(f)
      base == 'yayoi_all.pak' || base.start_with?('all_')
    end

    if source_paks.empty?
      puts "Warning: No source pak files found in build_staging to merge."
      return
    end

    target_pak = File.join(@build_dir, 'JP_Historical_all.pak')
    makeobj_tool.merge_paks(target_pak, source_paks)
  end

  def maketab
    puts "=== Step: Generating build/text/ja.tab and en.tab ==="
    FileUtils.mkdir_p(@build_text_dir)

    # 1. ja.tab
    jatab_files = Dir.glob("#{@base_dir}/**/*.jatab")
    base_ja = File.join(@base_dir, 'text', 'ja.tab')
    jatab_files << base_ja if File.exist?(base_ja)

    target_ja = File.join(@build_text_dir, 'ja.tab')
    File.open(target_ja, 'w', encoding: 'utf-8') do |out|
      out.print '§'
      jatab_files.uniq.each do |f|
        next unless File.exist?(f)
        File.readlines(f, encoding: 'utf-8').each do |line|
          out.puts line.chomp
        end
      end
    end
    puts "  Created: build/text/ja.tab (#{File.size(target_ja)} bytes)"

    # 2. en.tab
    entab_files = Dir.glob("#{@base_dir}/**/*.entab")
    base_en = File.join(@base_dir, 'text', 'en.tab')
    entab_files << base_en if File.exist?(base_en)

    target_en = File.join(@build_text_dir, 'en.tab')
    File.open(target_en, 'w', encoding: 'utf-8') do |out|
      out.print '§'
      entab_files.uniq.each do |f|
        next unless File.exist?(f)
        File.readlines(f, encoding: 'utf-8').each do |line|
          out.puts line.chomp
        end
      end
    end
    puts "  Created: build/text/en.tab (#{File.size(target_en)} bytes)"
  end

  def clean
    puts "=== Cleaning generated files ==="
    # Remove dat files generated from datt
    CATEGORIES.each do |cat|
      cat_dir = File.join(@base_dir, cat)
      next unless Dir.exist?(cat_dir)

      Dir.glob("#{cat_dir}/**/*.dat").each do |dat_file|
        datt_file = dat_file.sub(/\.dat$/, '.datt')
        if File.exist?(datt_file)
          puts "  Removing: #{dat_file.sub(@base_dir + '/', '')}"
          File.delete(dat_file)
        end
      end
    end

    # Remove jatab and entab files
    Dir.glob("#{@base_dir}/**/*.jatab").each { |f| File.delete(f) }
    Dir.glob("#{@base_dir}/**/*.entab").each { |f| File.delete(f) }

    # Clean staging paks
    if Dir.exist?(@build_staging)
      puts "  Cleaning build_staging/"
      FileUtils.rm_rf(Dir.glob("#{@build_staging}/*.pak"))
    end

    # Clean build
    if Dir.exist?(@build_dir)
      puts "  Cleaning build/"
      FileUtils.rm_rf(Dir.glob("#{@build_dir}/*.pak"))
      FileUtils.rm_rf(Dir.glob("#{@build_text_dir}/*.tab"))
    end
    puts "Clean finished."
  end
end

if __FILE__ == $0
  Make.new.run(ARGV)
end
