# 宋词 Data Source

`宋词.json` is generated from the `宋词/ci.song.*.json` files in
[`chinese-poetry/chinese-poetry`](https://github.com/chinese-poetry/chinese-poetry).

The source project is licensed under the MIT License:
<https://github.com/chinese-poetry/chinese-poetry/blob/master/LICENSE>.

Regenerate the local database with:

```shell
uv run python scripts/build_song_ci_database.py
```
