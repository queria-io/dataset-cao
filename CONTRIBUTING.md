# ビルドと更新

データセットの概要は [README.md](README.md) にあります。ここにはこのリポジトリでデータセットをビルド・更新する手順を書きます。

## ビルド

```bash
uv sync
uv run python main.py           # 取得して手元で dbt build（profiles.yml の環境変数が要る）
scripts/build.sh                # 取得・ビルドして Queria に公開する
```
