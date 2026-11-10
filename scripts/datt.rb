# encoding: utf-8

=begin
The MIT License (MIT)

Copyright (c) 2014 wa

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Pak128.Japan-Ex+Addonsチームが改造しています。改造箇所についてはgitの履歴を参照してください。
=end

begin
  require 'rubyXL'
rescue LoadError => e
  $stderr.puts <<~EOS
    rubyXL is not installed.
    Please install it with: gem install rubyXL
    rubyXLがインストールされていません。
    インストールするには、次のコマンドを実行してください。: gem install rubyXL
  EOS
  raise e
end

# Simutransのdatのプリプロセッサのようなもの。
module Datt

  ADDON_PREFIX = 'np-'

  # 代入文
  ASSIGN_LINE = /^([A-Za-z0-9_\[\]-]+)=(.+?)( *#.*)?$/
  # 分割
  SEPARATOR_LINE = /^-{2,}$/
  # コメント
  COMMENT_LINE = /^#(.*)$/
  # ディレクティブ
  DIRECTIVE_LINE = /^%(.+)$/
  # 遅延ディレクティブ
  DELAYED_DIRECTIVE_LINE = /^%%(.+)$/
  # 空行
  BLANK_LINE = /^$/
  # 画像指定の右辺
  IMAGE_REF = /(.+)\.(\d+)\.(\d+)/

  # dat(t)を行単位に分解するクラス
  class Lexer
    def initialize(io, filename)
      @io = io
      @filename = filename
      @line_number = 0
      @line = nil
      self.next
    end

    def next
      @last_match = nil
      @line = io.gets

      if @line
        @line.strip!
        @line_number += 1

        case @line
        when COMMENT_LINE
          @type = :comment
        when SEPARATOR_LINE
          @type = :separator
        when ASSIGN_LINE
          @type = :assign
        when BLANK_LINE
          @type = :blank
        when DELAYED_DIRECTIVE_LINE
          @type = :delayed_directive
        when DIRECTIVE_LINE
          @type = :directive
        else
          $stderr.printf "%s: unknown line: \n>>\n%s\n<<\n", location, @line
          @type = :unknown
        end
        @last_match = Regexp.last_match
      else
        @type = :eof
      end
    end

    def location
      sprintf('%s[%i]', File.basename(@filename), @line_number)
    end

    attr_reader :io

    attr_reader :filename

    attr_reader :line

    attr_reader :line_number

    attr_reader :type

    attr_reader :last_match
  end

  # アドオンブロック。「---」で区切られた一つの領域
  class Block
    def initialize(workspace, addon = nil, excel_variables = {})
      @workspace = workspace
      @addon = addon
      @lines = []
      @dat_variables = {}
      @excel_variables = excel_variables # pak名をキーとした配列、要素は各パラメータのHash
      @location = nil
      @fiename = nil
    end

    # ○:image属性からの相対指定
    def img(y, x)
      fail 'image not found' unless  @dat_variables[:image] =~ IMAGE_REF
      format('%s.%i.%i', $1, $2.to_i + y, $3.to_i + x)
    end

    # ●image属性と、level属性から適当に名前を決定する
    def do_autoname(id = nil)
      name = ADDON_PREFIX

      fail 'image not found' unless  @dat_variables[:image] =~ IMAGE_REF
      image_name = $1

      image_name = $1 if image_name =~ /(.+)-\d+$/
      name += image_name

      name += '-' + sprintf('%02d', id) if id

      push_dat_line "name=#{name}"
    end

    # ●タイル画像用のdatを出力する。
    def do_buil_image(xw, yw, h, dims, seasons, front: false)
      fail 'image not found' unless @dat_variables[:image] =~ IMAGE_REF
      fn = $1
      by = $2.to_i
      bx = $3.to_i

      push_dat_line "dims=#{xw},#{yw},#{dims}"

      mw = [xw, yw].max
      dw = mw * dims
      mh = mw * h
      fb_count = (front ? 2 : 1)
      fb_count.times do |fb|
        fbname = (fb == 0 ? 'backImage' : 'frontImage')

        seasons.times do |season|
          push_dat_line ''

          dims.times do |dim|
            if dim.even?
              txw, tyw = xw, yw
            else
              txw, tyw = yw, xw
            end
            tx = bx + fb * dw + dim * mw
            ty = by + season * mh + (h - 1)

            tyw.times do |y|
              txw.times do |x|
                h.times do |z|
                  lh = sprintf('%s[%i][%i][%i][%i][%i][%i]', fbname, dim, y, x, z, 0, season)
                  rh = sprintf('%s.%i.%i', fn, ty + y * h - z, tx + x)
                  prefix = (x > 0 && y > 0 && z > 0 ? '#' : '')
                  push_dat_line "#{prefix}#{lh}=#{rh}"
                end
              end
            end
          end
        end
      end
    end

    # ●別のファイルを読み込む。
    def do_require(path, addon: nil)
      path = File.expand_path(path, File.dirname(@filename))
      @workspace.require path, addon, @excel_variables
    end

    # ●他の定義を取り込む
    def do_include(s, label: false, overwrite: true)
      block = @workspace.get_block(s)

      @lines << '' << "#>>> #{block.location}" if label

      if overwrite
        block.dat_variables.keys.each do |v|
          do_undef v
        end
      end
      block.lines.each do |l|
        if l =~ DELAYED_DIRECTIVE_LINE
          # 遅延ディレクティブの場合、%を一つ減らして、後で評価する
          @lines << l[1..-1]
        elsif l =~ DIRECTIVE_LINE
          # ディレクティブの場合、評価する
          eval_derective($1)
        elsif l =~ ASSIGN_LINE && @dat_variables.include?($1.downcase.to_sym)
          @lines << '#' + l
        else
          @lines << l
        end
      end
      @dat_variables = block.dat_variables.merge(@dat_variables)

      @lines << '#<<<' << '' if label
    end

    # Excelファイルを読み込む
    def do_require_excel(path)
      excel_path = File.expand_path(path, File.dirname(@filename))
      begin
        workbook = RubyXL::Parser.parse(excel_path)
      rescue Zip::Error
        raise <<~EOS
          Excel file '#{excel_path}' is not found or is not a valid Excel file.
          Excelファイル '#{excel_path}' が見つからないか、正しいExcelファイルではありません。
        EOS
      end
      worksheet = workbook['parameters']
      raise <<~EOS unless worksheet
        Excel worksheet 'parameters' not found in file '#{excel_path}'.
        Excelファイル '#{excel_path}' にワークシート 'parameters' が見つかりません。
      EOS
      # 1行目にラベルがあるので、セルが空になるまでループでラベルを取得する
      labels = {}
      worksheet[0].cells.each do |cell|
        break if cell.nil? || cell.value.nil? || cell.value.strip.empty?
        labels[cell.value.strip.downcase] = cell.column
      end
      # @excel_variablesにパラメータを格納する
      # nameをキーにして、ラベルに沿って各パラメータの値をハッシュで格納する
      worksheet.each_with_index do |row, row_index|
        next if row_index <= 2 # 1行目はラベル、2行目はその説明なのでスキップ
        name_pos = labels["name"]
        next if row.nil?
        name = row[name_pos]&.value&.strip
        # nameのセルが空ならスキップ
        next if name.nil? || name.empty?
        hash = Hash.new
        labels.each do |label, col|
          value = row[col]&.value
          hash[label] = value
        end
        # nameをキーにしてハッシュを格納
        @excel_variables[name] = hash
      end
    end

    # Excelで読み込んだパラメータを参照するための関数
    def excel(key, name = nil)
      name ||= @dat_variables[:name]
      raise <<~EOS if @excel_variables == {}
        Excel parameters not found. Please use %require_excel directive to load parameters from an Excel file.
        Excelパラメータが見つかりません。%require_excelディレクティブを使用して、Excelファイルからパラメータを読み込んでください。
      EOS
      raise <<~EOS if @excel_variables[name].nil?
        Excel parameters for '#{name}' not found. Please check the name.
        '#{name}'のExcelパラメータが見つかりません。名前を確認してください。
      EOS
      @excel_variables[name][key]
    end

    # excel関数と同じだが、パラメータが無いときにエラーを出す
    def excel!(key, name = nil)
      value = excel(key, name)
      raise <<~EOS if value.nil?
        Excel parameter '#{key}' for '#{name}' not found.
        '#{name}'のExcelパラメータ '#{key}' が見つかりません。
      EOS
      value
    end

    # ● #addonに値を設定する。
    def do_addon(v = true)
      @addon = v
    end

    # ●定義のみ追加する。シンボルはすべて小文字
    def do_def(s, e)
      @dat_variables[s] = e
    end

    # ●定義を削除する。一致判断は、===で行う。
    def do_undef(cond)
      @dat_variables.keys.each do |k|
        @dat_variables.delete k if cond === k.to_s
      end

      @lines.map! do |line|
        if line =~ ASSIGN_LINE && cond === $1.downcase
          '#' + line
        else
          line
        end
      end
    end

    # ●name属性を設定し、 #addon をfalseに設定する
    def do_resource(s)
      @dat_variables[:name] = s
      @addon = false
    end

    # jatabファイルを出力する。
    def do_ja(ja_name)
      $jatab.puts @dat_variables[:name]
      $jatab.puts ja_name
    end

    # entabファイルを出力する。
    def do_en(en_name)
      $entab.puts @dat_variables[:name]
      $entab.puts en_name
    end

    # Rubyのファイルを読み込む。全て相対パスで扱う
    # このコマンドは必ず.rb拡張子までfilenameに指定する必要がある
    def do_require_ruby(filename)
      if filename !~ /\.rb$/
        $stderr.puts <<~EOS
          %require_ruby directive requires a filename with .rb extension.
          %require_rubyディレクティブは、.rb拡張子を持つファイル名を指定する必要があります。
        EOS
        raise ArgumentError, 'filename must end with .rb'
      end
      filename = File.expand_path(filename, File.dirname(@filename))
      begin
        require filename
      rescue LoadError => e
        $stderr.puts <<~EOS
          Ruby file '#{filename}' is not found or is not a valid Ruby file.
          Rubyファイル '#{filename}' が見つからないか、正しいRubyファイルではありません。
          
          以下例外メッセージ
          #{e.message}
        EOS
        raise e
      end
    end

    # 入力された文字列を行単位に分解して、linesに追加する。
    def do_lines(lines)
      lines.each_line do |line|
        line.strip!
        next if line.empty? # 空行はスキップ
        if line.start_with?('#')
          # コメント行はそのまま追加
          push_dat_line line
        else
          # その他の行は評価して追加
          push_dat_line eval_macro(line)
        end
      end
    end

    # ソースを評価し、出力対象ならdatを出力する
    def eval_block(lexer)
      @location = lexer.location
      @filename = lexer.filename

      loop do
        case lexer.type
        when :directive
          eval_derective(lexer.last_match[1])
        when :delayed_directive
          @lines << "%#{lexer.last_match[1]}"
        when :assign, :comment, :blank, :unknown
          push_dat_line lexer.line
        else
          break
        end
        lexer.next
      end

      @workspace.blocks << self if @dat_variables.include?(:name)

      write_dat_block if write_dat_block?
    end

    def eval_derective(arg)
      instance_eval "do_#{arg}"
    rescue SyntaxError => e
      $stderr.puts "#{@location}: syntax error in directive: %#{arg}"
      raise e
    end

    # 評価結果に一行付け加える
    def push_dat_line(line)
      @lines << line

      if line =~ ASSIGN_LINE
        k = $1
        v = $2
        @dat_variables[k.downcase.to_sym] = v
      end
    end

    # 出力対象か？
    def write_dat_block?
      case @addon
      when true
        true
      when false
        false
      when nil
        @dat_variables.include?(:name)
      end
    end

    # 展開指示「#{}」を展開した文字列を返す
    def eval_macro(line)
      line.gsub(/#\{(.+?)\}/) do |m|
        instance_eval($1)
      rescue SyntaxError => e
        $stderr.puts "#{@location}: syntax error in macro: #{m}"
        raise e
      end
    end

    # 評価結果のdatソースを出力する。
    def write_dat_block
      puts '---'
      prev_line = nil
      @lines.each do |line|
        line = eval_macro(line).strip
        puts line unless line == '' && prev_line == ''
        prev_line = line
      end
    end

    # メンバが見つからない場合は、datの属性を参照させる。
    def method_missing(sym, *args)
      return @dat_variables[sym] if @dat_variables.include?(sym)
      fail "unknown method: #{sym}"
    end

    # ファイル名
    attr_reader :filename
    # ブロックが存在する位置を表す文字列。『ファイル名［行番号］』の形式
    attr_reader :location
    # 評価結果の配列
    attr_reader :lines
    # 属性値のハッシュ
    attr_reader :dat_variables
    # ブロックの評価結果を最終的に出力するか否かの状態。
    def addon?
      @addon
    end
  end

  # 作業領域
  class Workspace
    def initialize
      @blocks = []
      @loaded_files = []
    end

    # ファイルを読み込む。既に読み込み済みの場合は、読み込まない
    def require(filename, addon = nil, excel_parameters = {})
      key = File.basename(filename).downcase

      return if @loaded_files.include?(key)

      @loaded_files << key
      File.open(filename, 'r') do |io|
        eval_datt io, filename, addon, excel_parameters
      end
    end

    # Blockを探す
    def get_block(name)
      @blocks.each do |blk|
        return blk if blk.name == name
      end
      fail "block not found: #{name}"
    end

    # ファイルを読み込む
    def eval_datt(io, filename, addon = nil, excel_parameters = {})
      lexer = Lexer.new(io, filename)

      lexer.next while lexer.type == :comment
      lexer.next if lexer.type == :separator

      loop do
        case lexer.type
        when :assign, :comment, :directive, :blank, :unknown
          Block.new(self, addon, excel_parameters).eval_block(lexer)
        else
          break
        end

        break unless lexer.type == :separator
        lexer.next
      end

      fail "#{lexer.location}: eof expected" unless lexer.type == :eof
    end

    attr_reader :blocks
  end
end

