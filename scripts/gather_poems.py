"""Script to gather 300 Tang Poems and save them locally."""

import requests
import json
import os
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
import time


def fetch_from_gushi_ci_api() -> List[Dict]:
    """Fetch poems from gushi.ci API."""
    try:
        print("正在从 gushi.ci API 获取数据...")
        api_url = "https://api.gushi.ci/all.json"
        
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        poems_data = response.json()
        
        # Filter for Tang dynasty poems
        tang_poems = []
        for poem in poems_data:
            dynasty = poem.get('dynasty', '')
            if dynasty == '唐' or '唐' in str(dynasty):
                tang_poems.append({
                    'title': poem.get('title', '无题'),
                    'author': poem.get('author', '未知'),
                    'dynasty': poem.get('dynasty', '唐'),
                    'content': poem.get('content', ''),
                    'translation': poem.get('translation', '')
                })
        
        print(f"从 API 获取到 {len(tang_poems)} 首唐诗")
        return tang_poems[:300]  # Limit to 300
    
    except Exception as e:
        print(f"API 获取失败: {e}")
        return []


def fetch_from_github_dataset() -> List[Dict]:
    """Fetch from GitHub Chinese Poetry dataset."""
    try:
        print("尝试从 GitHub 中文诗歌数据集获取...")
        tang_poems = []
        
        # The Chinese Poetry GitHub repo has multiple JSON files
        # Try fetching from multiple files to get more poems
        base_url = "https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/master/json/poet.tang."
        
        for i in range(10):  # Try first 10 files (each contains many poems)
            try:
                url = f"{base_url}{i}.json"
                print(f"  正在获取文件 {i}...")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                poems_data = response.json()
                
                for poem in poems_data:
                    paragraphs = poem.get('paragraphs', [])
                    if paragraphs:
                        tang_poems.append({
                            'title': poem.get('title', '无题'),
                            'author': poem.get('author', '未知'),
                            'dynasty': '唐',
                            'content': '\n'.join(paragraphs),
                            'translation': ''
                        })
                
                # If we have enough, break
                if len(tang_poems) >= 300:
                    break
                    
                time.sleep(0.5)  # Be polite to GitHub
                
            except Exception as e:
                print(f"  文件 {i} 获取失败: {e}")
                continue
        
        # Remove duplicates
        seen = set()
        unique_poems = []
        for poem in tang_poems:
            key = (poem['title'], poem['author'])
            if key not in seen:
                seen.add(key)
                unique_poems.append(poem)
        
        print(f"从 GitHub 数据集获取到 {len(unique_poems)} 首唐诗")
        return unique_poems[:300]
    
    except Exception as e:
        print(f"GitHub 数据集获取失败: {e}")
        return []


def get_extended_fallback_poems() -> List[Dict]:
    """Extended fallback with more famous Tang poems."""
    return [
        {
            'title': '静夜思',
            'author': '李白',
            'dynasty': '唐',
            'content': '床前明月光，疑是地上霜。\n举头望明月，低头思故乡。',
            'translation': ''
        },
        {
            'title': '春晓',
            'author': '孟浩然',
            'dynasty': '唐',
            'content': '春眠不觉晓，处处闻啼鸟。\n夜来风雨声，花落知多少。',
            'translation': ''
        },
        {
            'title': '登鹳雀楼',
            'author': '王之涣',
            'dynasty': '唐',
            'content': '白日依山尽，黄河入海流。\n欲穷千里目，更上一层楼。',
            'translation': ''
        },
        {
            'title': '咏鹅',
            'author': '骆宾王',
            'dynasty': '唐',
            'content': '鹅，鹅，鹅，曲项向天歌。\n白毛浮绿水，红掌拨清波。',
            'translation': ''
        },
        {
            'title': '悯农',
            'author': '李绅',
            'dynasty': '唐',
            'content': '锄禾日当午，汗滴禾下土。\n谁知盘中餐，粒粒皆辛苦。',
            'translation': ''
        },
        {
            'title': '望庐山瀑布',
            'author': '李白',
            'dynasty': '唐',
            'content': '日照香炉生紫烟，遥看瀑布挂前川。\n飞流直下三千尺，疑是银河落九天。',
            'translation': ''
        },
        {
            'title': '早发白帝城',
            'author': '李白',
            'dynasty': '唐',
            'content': '朝辞白帝彩云间，千里江陵一日还。\n两岸猿声啼不住，轻舟已过万重山。',
            'translation': ''
        },
        {
            'title': '赠汪伦',
            'author': '李白',
            'dynasty': '唐',
            'content': '李白乘舟将欲行，忽闻岸上踏歌声。\n桃花潭水深千尺，不及汪伦送我情。',
            'translation': ''
        },
        {
            'title': '黄鹤楼送孟浩然之广陵',
            'author': '李白',
            'dynasty': '唐',
            'content': '故人西辞黄鹤楼，烟花三月下扬州。\n孤帆远影碧空尽，唯见长江天际流。',
            'translation': ''
        },
        {
            'title': '绝句',
            'author': '杜甫',
            'dynasty': '唐',
            'content': '两个黄鹂鸣翠柳，一行白鹭上青天。\n窗含西岭千秋雪，门泊东吴万里船。',
            'translation': ''
        },
        {
            'title': '春夜喜雨',
            'author': '杜甫',
            'dynasty': '唐',
            'content': '好雨知时节，当春乃发生。\n随风潜入夜，润物细无声。\n野径云俱黑，江船火独明。\n晓看红湿处，花重锦官城。',
            'translation': ''
        },
        {
            'title': '登高',
            'author': '杜甫',
            'dynasty': '唐',
            'content': '风急天高猿啸哀，渚清沙白鸟飞回。\n无边落木萧萧下，不尽长江滚滚来。\n万里悲秋常作客，百年多病独登台。\n艰难苦恨繁霜鬓，潦倒新停浊酒杯。',
            'translation': ''
        },
        {
            'title': '相思',
            'author': '王维',
            'dynasty': '唐',
            'content': '红豆生南国，春来发几枝。\n愿君多采撷，此物最相思。',
            'translation': ''
        },
        {
            'title': '山居秋暝',
            'author': '王维',
            'dynasty': '唐',
            'content': '空山新雨后，天气晚来秋。\n明月松间照，清泉石上流。\n竹喧归浣女，莲动下渔舟。\n随意春芳歇，王孙自可留。',
            'translation': ''
        },
        {
            'title': '送元二使安西',
            'author': '王维',
            'dynasty': '唐',
            'content': '渭城朝雨浥轻尘，客舍青青柳色新。\n劝君更尽一杯酒，西出阳关无故人。',
            'translation': ''
        },
        {
            'title': '回乡偶书',
            'author': '贺知章',
            'dynasty': '唐',
            'content': '少小离家老大回，乡音无改鬓毛衰。\n儿童相见不相识，笑问客从何处来。',
            'translation': ''
        },
        {
            'title': '咏柳',
            'author': '贺知章',
            'dynasty': '唐',
            'content': '碧玉妆成一树高，万条垂下绿丝绦。\n不知细叶谁裁出，二月春风似剪刀。',
            'translation': ''
        },
        {
            'title': '凉州词',
            'author': '王翰',
            'dynasty': '唐',
            'content': '葡萄美酒夜光杯，欲饮琵琶马上催。\n醉卧沙场君莫笑，古来征战几人回。',
            'translation': ''
        },
        {
            'title': '出塞',
            'author': '王昌龄',
            'dynasty': '唐',
            'content': '秦时明月汉时关，万里长征人未还。\n但使龙城飞将在，不教胡马度阴山。',
            'translation': ''
        },
        {
            'title': '芙蓉楼送辛渐',
            'author': '王昌龄',
            'dynasty': '唐',
            'content': '寒雨连江夜入吴，平明送客楚山孤。\n洛阳亲友如相问，一片冰心在玉壶。',
            'translation': ''
        }
    ]


def gather_poems() -> List[Dict]:
    """Gather poems from various sources."""
    poems = []
    
    # Try primary API
    poems = fetch_from_gushi_ci_api()
    
    # If not enough, try GitHub dataset
    if len(poems) < 50:
        alt_poems = fetch_from_github_dataset()
        if alt_poems:
            poems = alt_poems
    
    # If still not enough, add fallback poems
    if len(poems) < 20:
        print("使用扩展的备用数据...")
        fallback = get_extended_fallback_poems()
        poems.extend(fallback)
        # Remove duplicates
        seen = set()
        unique_poems = []
        for poem in poems:
            key = (poem['title'], poem['author'])
            if key not in seen:
                seen.add(key)
                unique_poems.append(poem)
        poems = unique_poems
    
    # Limit to 300
    poems = poems[:300]
    
    return poems


def save_poems(poems: List[Dict], filepath: str):
    """Save poems to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(poems, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(poems)} 首诗歌到 {filepath}")


def main():
    """Main function."""
    # Create data directory if it doesn't exist
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    poems_file = data_dir / "tang_poems.json"
    
    print("=" * 50)
    print("开始收集《唐诗三百首》数据...")
    print("=" * 50)
    
    poems = gather_poems()
    
    if poems:
        save_poems(poems, str(poems_file))
        print(f"\n成功收集并保存了 {len(poems)} 首唐诗！")
        print(f"文件位置: {poems_file}")
    else:
        print("\n未能收集到诗歌数据。")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

