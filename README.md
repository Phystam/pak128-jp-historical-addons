# Simutrans アドオン作成・管理環境ガイド

本プロジェクトでは、カテゴリごとのフォルダ分割と、`datt` (Rubyプリプロセッサ) および Google スプレッドシート / Excel (`parameters.xlsx`) によるアドオンの一括管理・自動ビルド環境を整備しています。

---

## 1. ディレクトリ構成

ルート直下は以下の9大カテゴリに整理されています。すべて英数字フォルダ名で管理されます。

```
Simutrans/
├── buildings/        # 建物類 (駅舎等用extension含まない: 住宅・商業・寺社・集落等)
├── Industries/       # 産業類 (工場、水田・農地、原料採掘等)
├── ways/             # 道路・運河・線路等の交通インフラ
├── way-objects/      # 架線・柵・逆茂木等のway-object
├── stations/         # 駅舎、停留所、埠頭/港、車庫(depot)、造船所
├── vehicles/         # 車両 (運搬人、船舶、列車等)
├── citycars/         # 市内一般車両
├── pedestrians/      # 歩行者
├── crossings/        # 異なるway同士の平面交差
├── goods/            # 貨物定義
├── text/             # 言語リソース (ja.tab, en.tab 元データ)
├── build_staging/    # makeobj による個別 pak の一時出力先
├── build/            # 統合 pak 出力先 (yayoi_all.pak, build/text/ja.tab)
├── scripts/          # ビルド・同期スクリプト群
└── build.bat         # 一括ビルド用バッチファイル
```

---

## 2. パラメータ管理 (Google スプレッドシート / Excel)

各カテゴリの直下に、パラメータ管理用の `parameters.xlsx` が配置されています。

### 編集方法
1. **Google ドライブの Web 上で直接編集 (推奨)**:
   Google ドライブ上で `parameters.xlsx` を開くと、**Google スプレッドシート**として直接編集・保存できます（Google Workspace Office 編集機能）。
2. **Google スプレッドシート (.gsheet) との連携**:
   Google ドライブ上で新規「Google スプレッドシート」を作成した場合や、公開URLがある場合、各カテゴリ直下の `.gsheet` または `spreadsheet_url.txt` を自動認識して最新データをローカルに同期します。

### シートの構造 (`parameters` シート)
- **1行目 (ヘッダ)**: パラメータ名（小文字、例: `addon`, `name`, `japanese`, `english`, `intro_year`, `cost` 等）
- **2行目 (説明文)**: 日本語の説明
- **3行目 (サンプル行)**: `addon` を `"無視"` に設定したサンプル
- **4行目以降 (データ行)**: 個別アドオンのパラメータ。ビルド対象は `addon` に `"含"` を入力します。

---

## 3. datt テンプレートの仕組み

1. **カテゴリマスター (`<category>.datt`)**:
   各カテゴリ直下に配置（例: `buildings/buildings.datt`, `ways/ways.datt`）。
   `%require_excel 'parameters.xlsx'` により Excel の値を読み込み、計算式や共通パラメータを展開します。
2. **個別アドオン (`<addon>.datt`)**:
   各アドオンフォルダ内に配置（例: `buildings/sanctuary/shusaiden/shusaiden.datt`）。
   親のマスター datt を `%require` し、`name=<ID>` を指定して `%include '<category>'` することで、画像定義以外のパラメータを一括バインドします。

---

## 4. ビルドコマンド

### ワンクリック実行
プロジェクト直下の **`build.bat`** をダブルクリックするだけで、全パイプラインが一気通貫で走ります。

### コマンドライン実行 (PowerShell / コマンドプロンプト)
```bash
# 全パイプライン一括実行 (sync -> makedat -> makeobj -> merge -> tab)
ruby scripts/make.rb all

# Google スプレッドシートとの同期のみ
ruby scripts/make.rb sync

# datt から dat と jatab を生成
ruby scripts/make.rb makedat

# dat から build_staging/ に個別 pak を生成
ruby scripts/make.rb makeobj

# build_staging/ の pak をマージして build/yayoi_all.pak を生成
ruby scripts/make.rb merge

# build/text/ja.tab を生成
ruby scripts/make.rb tab

# 生成物 (dat, jatab, staging pak, build pak) のクリーンアップ
ruby scripts/make.rb clean
```

---

## 5. 生成される成果物

- **統合 pak**: `build/yayoi_all.pak`
  Simutrans の `addons/pak128` などにそのまま配置して利用できます。
- **翻訳ファイル**: `build/text/ja.tab` (および `en.tab`)
  各アドオンの日本語名称および基本貨物定義を結合した UTF-8 (BOM/§ 付き) ファイルです。
