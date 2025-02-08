# デプロイ手順書

本手順書では、Azure 上にカスタムフローをデプロイするまでの一連の作業を示します。  
**お客様自身が同様の手順を再現できるよう**、できるだけ丁寧に記載しています。

---

## 1. 前提条件

以下のソフトウェアや環境があらかじめ用意されていることを確認してください。

1. **Azure CLI** がインストールされていること  
   - バージョンの確認例: `az version`
2. **Docker for Linux (または Docker CLI)** がインストールされており、起動していること  
   - バージョンの確認例: `docker -v`
3. **Azure CLI でログインしていること**  
   - コマンド例: `az login`
4. **Python 3.9 以上**がインストールされていること  
   - バージョンの確認例: `python --version`

---

## 2. 環境セットアップ

### 2.1 フローの置き換え
1. `advanced_rag_custom/flow.dag.sample.yml` を `advanced_rag_custom/flow.dag.yml` にリネームします。
   ```bash
   mv advanced_rag_custom/flow.dag.sample.yml advanced_rag_custom/flow.dag.yml
   ```
   ※Windows 環境の場合はエクスプローラー上でファイル名を変更していただくか、  
   `rename` コマンドを利用してください。

### 2.2 仮想環境の作成
1. プロジェクトのルートディレクトリに移動し、次のコマンドを実行して仮想環境を作成します。
   ```bash
   python -m venv .venv
   ```

### 2.3 仮想環境の有効化
1. **Linux/Mac**の場合:
   ```bash
   source .venv/bin/activate
   ```
2. **Windows (PowerShell)** の場合:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   ※PowerShell の実行ポリシーによっては `Set-ExecutionPolicy` の設定が必要な場合があります。

### 2.4 ライブラリのインストール
1. 仮想環境が有効化されている状態で、以下のコマンドを実行し、必要なライブラリをインストールします。
   ```bash
   pip install -r requirements.txt
   ```

### 2.5 pf コマンドが有効になっているか確認
1. 下記のコマンドで `pf`(PromptFlow CLI) が正しくインストールされているかを確認します。
   ```bash
   pf --version
   ```
   バージョン番号が表示されれば OK です。

---

## 3. Flow の作成 / 動作確認

### 3.1 コネクションの作成
AI Gateway などへの接続情報を持つコネクションを作成します。

```bash
pf connection create \
  -f custom.yml \
  --set configs.endpoint="AI Gateway のエンドポイント" \
         secrets.sub_key="AI Gateway のサブスクリプションキー"
```

- **AI Gateway のエンドポイント**  
  `https://{APIM のリソース名}.azure-api.net/openai/deployments/{モデルのデプロイ名}/chat/completions?api-version={API バージョン}`  
  の形式を想定しています。

### 3.2 フローの変更
1. `advanced_rag_custom/flow.dag.yml` をエディタで開き、`lookup00` ノード部分を自身の環境に合わせて修正してください。

   例:
   ```yaml
   - name: lookup00
     type: python
     source:
       type: package
       tool: promptflow_vectordb.tool.common_index_lookup.search
     inputs:
       mlindex_content: >
       ...
   ```

   **mlindex_content** に指定されている値等を、適切なパスや内容に置き換えてください。  

2. 変更後は保存して終了します。

(確認イメージ)  
![Flowの変更例](https://github.com/user-attachments/assets/4b4b6280-89ab-46fa-9079-bcbfe8d91ef0)

---

## 4. デプロイ

### 4.1 リソースグループの作成
まず、Azure 上にリソースをまとめるためのリソースグループを作成します。

```bash
az group create \
  --name "<リソースグループ名>" \
  --location japaneast
```

### 4.2 Azure Container Registry (ACR) の作成
次に、ACR を作成します。(管理者ユーザーを ON にします)

```bash
az acr create \
  --resource-group "<リソースグループ名>" \
  --name "<ACR名>" \
  --sku Standard \
  --admin-enabled true \
  --location japaneast
```

### 4.3 フローのビルド (Docker イメージ化)
1. フローを Docker イメージとしてビルドするため、以下のコマンドを実行します。
   ```bash
   pf flow build \
     --source ./advanced_rag_custom \
     --output dist \
     --format docker
   ```

   - `--output` で指定した `dist` ディレクトリに成果物が出力されます。

### 4.4 ビルド成果物から不要な情報を削除
ビルド後に生成されるファイル内に、不要な API キー行が含まれるため、手動で削除します。

1. `dist/connections/custom.yml`
   ```yaml
   $schema: https://azuremlschemas.azureedge.net/promptflow/latest/CustomConnection.schema.json
   type: custom
   name: custom_connection_custom
   configs:
     key1: test1
     endpoint_url: # エンドポイントのURL
   secrets:
     api-key: ${env:CUSTOM_CONNECTION_CUSTOM_API-KEY} ← この行を削除
     sub_key: ${env:CUSTOM_CONNECTION_CUSTOM_SUB_KEY}
   module: promptflow.connections
   ```
   `api-key: ${env:CUSTOM_CONNECTION_CUSTOM_API-KEY}` の行を削除してください。

2. `dist/settings.json`
   ```json
   {
     "CUSTOM_CONNECTION_CUSTOM_API-KEY": "", ← この行を削除
     "CUSTOM_CONNECTION_CUSTOM_SUB_KEY": ""
   }
   ```
   `"CUSTOM_CONNECTION_CUSTOM_API-KEY": ""` の行を削除してください。

### 4.5 フローのデプロイ (App Service への配置)
1. PowerShell スクリプト `deploy.ps1` を使用し、Docker イメージを ACR にプッシュしたうえで App Service を作成・配置します。

   ```powershell
   .\deploy.ps1 -Path dist `
     -i "sample-app:v1" `
     -n "<App Service のリソース名>" `
     -r "<ACR のリソース名>.azurecr.io" `
     -g "<リソースグループ名>" `
     -l "japaneast" `
     -sku "<SKUの名前>"
   ```
   | パラメーター | 説明 |
   |--------------|----------------------------------------|
   | `-Path`      | ビルド成果物のパス (ここでは `dist`)   |
   | `-i`         | Docker イメージ名:タグ (例: `sample-app:v1`) |
   | `-n`         | App Service のリソース名 |
   | `-r`         | ACR のログインサーバー名 (末尾に `.azurecr.io` がつく) |
   | `-g`         | リソースグループ名 |
   | `-l`         | ロケーション (例: `japaneast`) |
   | `-sku`       | App Service のプラン SKU (例: `B1`, `S1` など) |

### 4.6 App Service の環境変数の設定
1. Azure Portal にアクセスし、作成した App Service の「構成」画面からアプリケーション設定 (環境変数) を編集します。
2. 下記のキーと値を追加してください。

   - `CUSTOM_CONNECTION_CUSTOM_SUB_KEY`: **AI Gateway のサブスクリプションキー**  
   - `BUILD_INFO`: `{"build_number": "1"}` (任意のバージョン情報を格納できるようにしている例)

(設定イメージ)  
![App Service の構成画面](https://github.com/user-attachments/assets/74102de3-acae-438a-9ed5-0c68fe3b3b38)

### 4.7 App Service に Azure ML ワークスペースの閲覧権限を付与

#### 4.7.1 App Service のマネージド ID を有効化
1. Azure Portal 上で当該の App Service の「設定」→「ID」を開き、  
   システム割り当てのマネージド ID を **有効** にします。
2. **保存** すると、自動的に Azure の AD でマネージド ID が付与されます。

(マネージド ID のイメージ)  
![マネージド ID 有効化](https://github.com/user-attachments/assets/5d0c4f2a-b793-4229-a615-ef9357a05654)

#### 4.7.2 ML データサイエンティストのロールを付与
1. Azure Portal で AI Foundry (または使用している Azure Machine Learning ワークスペース) が存在するリソースグループへ移動します。
2. 「アクセス制御(IAM)」→「ロールの割り当ての追加」を選択します。
3. **ロールの割り当ての追加** 画面で、ロールとして「ML データ科学者 (Azure ML Data Scientist)」を選択し、メンバーとして **App Service のマネージド ID** を選択します。

(ロール割り当てイメージ)  
![ロール割り当て](https://github.com/user-attachments/assets/a14c6b0a-7835-4776-8f72-df803517976e)
![MLデータ科学者選択](https://github.com/user-attachments/assets/b483994a-00b6-4e16-9fc5-ebb9126fc746)
![App Service のマネージド ID を選択](https://github.com/user-attachments/assets/221509b4-6762-4cfe-be4f-871e0f69eca9)

ロールが反映されるまで数分程度かかる場合があります。

### 4.8 App Service の URL にアクセスして動作確認
1. 数分後、ブラウザで下記 URL にアクセスします。
   ```
   https://<App Service のリソース名>.azurewebsites.net
   ```
2. デプロイしたフローが正しく動作するかを確認します。

(動作確認イメージ)  
![App Service 画面例](https://github.com/user-attachments/assets/dac881c9-5431-4228-ae30-287b645ae7c1)

---

## 5. その後の作業

- 現在はクエリ分割後のフローが 1 つにまとまっていますが、プロジェクトの要件に応じてクエリ拡張を行うなど、フローをカスタマイズしてください。

