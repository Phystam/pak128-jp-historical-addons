# Encoding: utf-8

if File.exist?('./scripts/datt.rb')
  require './scripts/datt'
else
  require 'datt'
end

class MakeDat
  def create_dat(datt_file, dat_file = nil, jatab_file = nil, entab_file = nil)
    dat_file ||= datt_file.sub(/\.datt$/, '.dat')
    jatab_file ||= datt_file.sub(/\.datt$/, '.jatab')
    entab_file ||= datt_file.sub(/\.datt$/, '.entab')

    wk = Datt::Workspace.new

    File.open(jatab_file, 'w:utf-8') do |jatab_output|
      $jatab = jatab_output
      File.open(entab_file, 'w:utf-8') do |entab_output|
        $entab = entab_output
        File.open(dat_file, 'w:utf-8') do |output|
          begin
            original_stdout = $stdout
            $stdout = output
            File.open(datt_file, 'r:utf-8') do |input|
              wk.eval_datt(input, datt_file, nil)
            end
          ensure
            $stdout = original_stdout
          end
        end
      end
    end
  end
end
