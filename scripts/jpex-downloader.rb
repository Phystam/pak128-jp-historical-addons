#!/usr/bin/env ruby

require 'net/http'
require 'json'
require 'uri'
require 'fileutils'

# リポジトリのリリース情報を取得するGitHub API URL
repo_url = 'https://api.github.com/repos/soukouki/simutrans-pak128.japan-ex-addons/releases'
destination_dir = './Pak128.Japan-Ex+Addons'
version_file = File.join(destination_dir, 'version.txt')

# 既存のバージョンをチェック
current_version = nil
if File.exist?(version_file)
  begin
    current_version = File.read(version_file).lines.first&.strip
    puts "現在のバージョン: #{current_version}"
  rescue
    puts "version.txtの読み込みに失敗しました"
  end
end

# 最新のリリース情報を取得
uri = URI(repo_url)
http = Net::HTTP.new(uri.host, uri.port)
http.use_ssl = true

request = Net::HTTP::Get.new(uri.request_uri)
request['User-Agent'] = 'Ruby Script'

response = http.request(request)
releases = JSON.parse(response.body)
# releasesを新しい順にソート
releases.sort_by! { |release| release['created_at'] }.reverse!

# 最新のリリースを取得（プレリリース含む）
latest_release = releases.first
release_version = latest_release['tag_name']
puts "最新のリリースバージョン: #{release_version}"

# バージョン比較とユーザー確認
if current_version
  if current_version == release_version
    puts "既に最新バージョンがインストールされています。"
    print "それでもダウンロードしますか？ (y/N): "
    answer = gets.chomp.downcase
    unless answer == 'y' || answer == 'yes'
      puts "ダウンロードをキャンセルしました。"
      exit
    end
  else
    puts "新しいバージョンが利用可能です。"
    print "#{current_version} → #{release_version} に更新しますか？ (y/N): "
    answer = gets.chomp.downcase
    unless answer == 'y' || answer == 'yes'
      puts "ダウンロードをキャンセルしました。"
      exit
    end
  end
end

# "Pak128.Japan-Ex+Addons.zip" という名前のアセットを探す
asset = latest_release['assets'].find { |a| a['name'] == 'Pak128.Japan-Ex+Addons.zip' }

if asset.nil?
  puts "Pak128.Japan-Ex+Addons.zip が見つかりません。"
  exit 1
end

# zipファイルをダウンロード
zip_url = asset['browser_download_url']
zip_file = 'Pak128.Japan-Ex+Addons.zip'

puts "Downloading #{zip_file}..."

# リダイレクトに対応してダウンロード
download_uri = URI(zip_url)
download_http = Net::HTTP.new(download_uri.host, download_uri.port)
download_http.use_ssl = true

download_request = Net::HTTP::Get.new(download_uri.request_uri)
download_response = download_http.request(download_request)

# 必要に応じてリダイレクトを追跡
if download_response.is_a?(Net::HTTPRedirection)
  redirect_uri = URI(download_response['location'])
  redirect_http = Net::HTTP.new(redirect_uri.host, redirect_uri.port)
  redirect_http.use_ssl = true
  download_response = redirect_http.get(redirect_uri.request_uri)
end

File.open(zip_file, 'wb') do |file|
  file.write(download_response.body)
end
puts 'Download complete.'

# ファイルを解凍
puts "Extracting #{zip_file}..."
FileUtils.rm_rf(destination_dir) if Dir.exist?(destination_dir)

# Windows/Linuxに対応した解凍コマンド
if Gem.win_platform?
  # Windowsの場合、標準のtarコマンドを使用（Windows 10以降で利用可能）
  system("tar -xf \"#{zip_file}\"")
else
  # Linux/macOSの場合、システムのunzipコマンドを使用
  system("unzip '#{zip_file}'")
end

# zipファイルを削除
File.delete(zip_file)
puts 'Extraction complete and zip file removed.'
