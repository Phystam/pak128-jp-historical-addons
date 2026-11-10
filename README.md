# Simutrans向けpak128 日本風歴史アドオンセット

本リポジトリは、交通シミュレーションゲーム『Simutrans』（pak128 / pak128.japan）向けに、日本の歴史時代（弥生時代〜古代を中心とした歴史的景観・インフラ・交通）を再現するためのアドオンセットおよびその統合開発環境です。

集落・建物（竪穴住居、高床倉庫、主祭殿、物見櫓等）、インフラ（環濠、土道、柵、河川港、造船所）、交通機関（運搬人、準構造船、丸木船等）、産業チェーン（水田・米、土器工房等）などを網羅し、Blenderによる3Dモデリングからdattプリプロセッサによる一括管理、makeobjによる自動パッケージングまでをワンストップで行えるパイプラインを備えています。

---

## 1. 開発・作成環境の構築指南

本プロジェクトのアドオンモデリングおよびスプライト生成は、**Blender** と専用のアドオン **Simutrans Blender Kit**、そしてAIコーディングエージェントとの協調作業を可能にする **Blender MCP** をベースに構築されています。

### ① 使用するBlenderのバージョン
- **推奨バージョン**: **Blender 5.2**（または Blender 4.x 以降）
  - 本リポジトリのモデルデータ (`.blend`) やシェーダーノード構成は、Blender 4.x〜5.x の新しいレンダーパイプライン（Principled BSDF の改訂、EEVEE-Next、Python API 仕様）に対応しています。

### ② Blender MCP の導入（AIエージェント連携環境）
AIエージェント（Antigravity等）がBlenderのシーン解析、Pythonスクリプト実行 (`bpy`/`bmesh`)、モデリング、レンダリング、視覚検証を自律的に行うためのMCPサーバーです。

1. **アドオンのインストール**:
   - `uv` が導入されている環境の場合、以下のコマンドで一発インストールが可能です：
     ```bash
     uvx mcp-for-blender install-addon
     ```
   - または、`blender_mcp.py` を Blender のアドオンフォルダに直接配置します：
     `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\blender_mcp.py`
2. **アドオンの有効化**:
   - Blenderを起動し、`Edit` > `Preferences` > `Add-ons` から **Blender MCP**（または `blender_mcp`）を検索してチェックを入れて有効化します。

### ③ Simutrans Blender Kit の導入とアンチエイリアシング修正
Blender上でSimutrans規格（pak128用等角投影カメラ・画面固定サンライト・タイルスライス・スプライトシート結合）を自動化するための必須アドオンです。

#### 1. アドオンの配置
`simutrans_blender_kit` フォルダを、Blenderのアドオンディレクトリに配置します：
`%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\simutrans_blender_kit\`

#### 2. アドオンの修正（アンチエイリアシング対応）
> [!IMPORTANT]
> **公式/初期状態の課題**:
> オリジナルの `simutrans_blender_kit` はスプライトのエッジを強調するため、内部で `scene.render.filter_size = 0.0`（アンチエイリアシング無効）が強制設定されています。
> これにより生成画像のエッジに強いジャギー（ギザギザ）が発生し、pak128.japanなどの既存アドオンの柔らかな風合いと混ぜた際に著しく浮いてしまう問題があります。

本プロジェクトの品質基準を満たすため、アドオンソースに対して以下の改修を適用しています：

- **`addon/ui.py` の修正**:
  `Scene.simutrans` プロパティおよび3Dビューのサイドバーパネルに、アンチエイリアシング設定項目を追加します。
  ```python
  # プロパティ定義 (PropertyGroup内)
  anti_aliasing: BoolProperty(
      name="Anti-Aliasing",
      description="Enable pixel filter smoothing to blend naturally with pak128.japan",
      default=True
  )
  filter_size: FloatProperty(
      name="Filter Size",
      description="Filter width for anti-aliasing (recommended: 1.5)",
      default=1.5,
      min=0.5,
      max=3.0
  )
  ```
  サイドバー（Simutransタブ）のレンダー設定UIに以下を描画：
  ```python
  row = layout.row(align=True)
  row.prop(p, "anti_aliasing", toggle=True)
  if p.anti_aliasing:
      row.prop(p, "filter_size", text="Radius")
  ```

- **`addon/rig.py` の修正**:
  カメラ・レンダリングリグ構築時 (`build_rig`) およびレンダリング時に、ユーザー設定値が反映されるように変更します。
  ```python
  use_aa = getattr(p, "anti_aliasing", False) if p else False
  f_size = getattr(p, "filter_size", 1.5) if p else 1.5
  if hasattr(r, "filter_size"):
      r.filter_size = f_size if use_aa else 0.0
  ```

- **制作時の推奨設定**:
  - `bpy.context.scene.simutrans.anti_aliasing = True`
  - `bpy.context.scene.simutrans.filter_size = 1.5`
  （※ 詳細は [`simutrans_blender.md`](./simutrans_blender.md) を参照）

### ④ レンダリング時の原色混入（Z-fightingノイズ）の注意点
Simutrans Blender Kitによるレンダリング時、低解像度の直交投影（等角投影）環境において、メッシュ同士がミリ単位でスレスレに重なり合っている部分（Z-fighting）や微小な鋭角交差（スライバーポリゴン）があると、深度バッファ判定やシェーダーの法線微分計算が破綻し、出力画像のエッジにマゼンタやシアン、蛍光グリーンなどの意図しない原色ノイズが混入する現象が発生します。

- **基本的な回避方針**:
  - 接合パーツ（柱、梁、棟木、千木など）は相手の表面スレスレで止めず、内部深くまでしっかりと埋め込む（貫通深度を確保する）。
  - 屋根の裾面は土台マウンドを完全に貫通して接地面（$Z=0$）まで落とし、同高度での面の近接・競合を避ける。
  - レンダリング後は `bpy.ops.simutrans.check_colors()` を実行し、異常ピクセルやSimutrans予約色（プレイヤーカラー、透過キー色等）の混入がないか確認する。

> [!TIP]
> 原色混入の詳しい発生メカニズムおよびモデリングでの具体的な修正手順については、[`simutrans_blender.md`（レンダリング時の原色混入対策）](./simutrans_blender.md#8-レンダリング時の原色混入z-fighting微小交差ノイズ対策) にまとめてあるのでそちらを確認してください。

### ⑤ ビルド環境の準備（Ruby・makeobj）
- **Ruby**: Ruby 3.x（`ruby -v` で確認可能。dattプリプロセッサおよびビルドパイプライン実行に必要）
  - 必要gem: `roo`（Excel読み込み用。`gem install roo`）
- **makeobj**: `makeobj/makeobj.exe` に配置済み（pak128対応バイナリ）

---

## 2. ディレクトリ構成

ルート直下は以下のカテゴリフォルダに整理されており、すべて英数字フォルダ名で統一されています。

```
Simutrans/
├── buildings/        # 建物類 (住宅・商業・寺社・集落等)
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
├── Texture/          # モデリング共通テクスチャ素材 (.png, .xcf)
├── components/       # 再利用可能な3Dプロップ素材 (井戸等)
├── makeobj/          # makeobj 実行バイナリ
├── scripts/          # ビルド・同期スクリプト群
├── build_staging/    # makeobj による個別 pak の一時出力先 (git管理外)
├── build/            # 統合 pak 出力先 (git管理外)
├── simutrans_blender.md # Blenderモデリング・レンダリング共通規約
├── build.bat         # 一括ビルド用バッチファイル
└── README.md         # 本ドキュメント
```

---

## 3. パラメータ管理 (Google スプレッドシート / Excel)

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

## 4. datt テンプレートの仕組み

1. **カテゴリマスター (`<category>.datt`)**:
   各カテゴリ直下に配置（例: `buildings/buildings.datt`, `ways/ways.datt`）。
   `%require_excel 'parameters.xlsx'` により Excel の値を読み込み、計算式や共通パラメータを展開します。
2. **個別アドオン (`<addon>.datt`)**:
   各アドオンフォルダ内に配置（例: `buildings/city_buildings/shusaiden/shusaiden.datt`）。
   親のマスター datt を `%require` し、`name=<ID>` を指定して `%include '<category>'` することで、画像定義以外のパラメータを一括バインドします。

---

## 5. ビルドコマンド

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

# build_staging/ の pak をマージして build/JP_Historical_all.pak を生成
ruby scripts/make.rb merge

# build/text/ja.tab を生成
ruby scripts/make.rb tab

# 生成物 (dat, jatab, staging pak, build pak) のクリーンアップ
ruby scripts/make.rb clean
```

---

## 6. 生成される成果物

- **統合 pak**: `build/JP_Historical_all.pak`
  Simutrans の `addons/pak128` や `addons/pak128.japan` などにそのまま配置して利用できます。
- **翻訳ファイル**: `build/text/ja.tab` (および `en.tab`)
  各アドオンの日本語名称および基本貨物定義を結合した UTF-8 (BOM/§ 付き) ファイルです。

---

## 7. ライセンス

本リポジトリの成果物は [CC0 1.0 Universal (Public Domain)](./LICENSE) の下で公開されています。
