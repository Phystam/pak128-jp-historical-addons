# Encoding: utf-8
require 'json'
require 'net/http'
require 'uri'
require 'fileutils'

# Google Spreadsheet / Google Drive 同期スクリプト
class SyncSheets
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
  ]

  def initialize(base_dir = '.')
    @base_dir = base_dir
  end

  def sync_all
    puts '=== Checking and Syncing Google Spreadsheets ==='
    CATEGORIES.each do |cat|
      cat_dir = File.join(@base_dir, cat)
      next unless Dir.exist?(cat_dir)

      sync_category(cat, cat_dir)
    end
    puts '=== Spreadsheet Sync Finished ==='
  end

  def sync_category(cat_name, cat_dir)
    target_xlsx = File.join(cat_dir, 'parameters.xlsx')

    # 1. Check for .gsheet file in the category directory
    gsheet_files = Dir.glob(File.join(cat_dir, '*.gsheet'))
    doc_id = nil

    if gsheet_files.any?
      gsheet_file = gsheet_files.first
      begin
        content = File.read(gsheet_file, encoding: 'utf-8')
        json = JSON.parse(content)
        doc_id = json['doc_id']
        url = json['url']
        if !doc_id && url =~ %r{/d/([a-zA-Z0-9_-]+)}
          doc_id = Regexp.last_match(1)
        end
        puts "[#{cat_name}] Found .gsheet file: #{File.basename(gsheet_file)} (Doc ID: #{doc_id})"
      rescue => e
        puts "[#{cat_name}] Warning: Failed to parse .gsheet: #{e.message}"
      end
    end

    # 2. Check for spreadsheet_url.txt if no .gsheet
    url_file = File.join(cat_dir, 'spreadsheet_url.txt')
    if !doc_id && File.exist?(url_file)
      content = File.read(url_file, encoding: 'utf-8').strip
      if content =~ %r{/d/([a-zA-Z0-9_-]+)}
        doc_id = Regexp.last_match(1)
        puts "[#{cat_name}] Found spreadsheet URL in #{File.basename(url_file)} (Doc ID: #{doc_id})"
      end
    end

    # 3. If doc_id found, attempt to download latest xlsx export
    if doc_id
      export_url = "https://docs.google.com/spreadsheets/d/#{doc_id}/export?format=xlsx"
      puts "[#{cat_name}] Fetching latest data from Google Sheets: #{export_url}"
      if download_file(export_url, target_xlsx)
        puts "[#{cat_name}] Successfully updated #{File.basename(target_xlsx)} from Google Spreadsheet!"
      else
        puts "[#{cat_name}] Note: Could not download from Google Sheets (may require permissions or offline). Using local #{File.basename(target_xlsx)}."
      end
    elsif File.exist?(target_xlsx)
      # Direct .xlsx mode (editable in Google Drive web via Office Editing)
      puts "[#{cat_name}] Local parameters.xlsx is ready."
    else
      puts "[#{cat_name}] Warning: Neither parameters.xlsx nor .gsheet found in #{cat_name}."
    end
  end

  private

  def download_file(url_str, dest_path, limit = 5)
    return false if limit == 0

    uri = URI.parse(url_str)
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = (uri.scheme == 'https')
    http.open_timeout = 5
    http.read_timeout = 10

    request = Net::HTTP::Get.new(uri.request_uri)
    response = http.request(request)

    case response
    when Net::HTTPSuccess
      File.binwrite(dest_path, response.body)
      true
    when Net::HTTPRedirection
      location = response['location']
      download_file(location, dest_path, limit - 1)
    else
      false
    end
  rescue => e
    false
  end
end

if __FILE__ == $0
  syncer = SyncSheets.new('.')
  syncer.sync_all
end
