"""
黄金价格提醒脚本
"""
import requests
import json
import sys
import os
from datetime import datetime, timezone, timedelta

# 强制输出立即刷新
sys.stdout.reconfigure(line_buffering=True)

print("=== 脚本开始执行 ===", flush=True)

BEIJING_TZ = timezone(timedelta(hours=8))

def is_trading_day():
    """判断是否为交易日"""
    try:
        today = datetime.now(BEIJING_TZ).strftime('%Y%m%d')
        print(f"检查交易日: {today}", flush=True)
        url = f"https://tool.bitefu.net/jiari/?d={today}"
        resp = requests.get(url, timeout=5)
        result = resp.text.strip()
        print(f"API 返回: {result}", flush=True)
        # 0=工作日，1=周末，2=节假日
        if result == '0':
            print("今日是工作日", flush=True)
            return True
        else:
            print(f"今日非工作日 (代码: {result})", flush=True)
            return False
    except Exception as e:
        print(f"获取交易日信息失败: {e}", flush=True)
        return True


def get_gold_price():
    """获取金价，带重试机制"""
    print("开始获取金价...", flush=True)
    
    # 【已修复】全部替换为 上金所 AU9999 现货 正确接口
    sources = [
        {"name": "新浪财经", "url": "https://hq.sinajs.cn/list=SGE_AU9999", "parser": parse_sina, "encoding": "gbk", "retry": 2},
        {"name": "东方财富", "url": "https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=1&secid=88.AU9999&fields=f43", "parser": parse_eastmoney, "encoding": "utf-8", "retry": 2},
    ]
    
    for source in sources:
        for attempt in range(source.get("retry", 1)):
            try:
                print(f"尝试 {source['name']} (第{attempt+1}次)...", flush=True)
                resp = requests.get(source['url'], timeout=10)
                if source.get("encoding"):
                    resp.encoding = source["encoding"]
                
                if source['name'] == '新浪财经':
                    price = source['parser'](resp.text)
                else:
                    try:
                        price = source['parser'](resp.json())
                    except:
                        price = None
                
                if price and price > 0:
                    # 验证价格合理性（AU9999 历史范围 400-1500 元/克）
                    if 400 < price < 1500:
                        print(f"成功: {source['name']} 价格 {price}", flush=True)
                        return price, source['name']
                    else:
                        print(f"{source['name']} 返回价格 {price} 超出合理范围，跳过", flush=True)
                        break
            except Exception as e:
                print(f"{source['name']} 失败: {e}", flush=True)
                continue
    
    print("所有数据源均失败", flush=True)
    return None, None

# 【已修复】正确解析新浪 上金所 AU9999
def parse_sina(text):
    try:
        start = text.find('"')
        end = text.rfind('"')
        if start == -1 or end == -1:
            return None
        data = text[start+1:end].split(',')
        if len(data) >= 4:
            return float(data[3])
    except:
        pass
    return None

# 【废弃不用，保留函数不删】
def parse_tencent(data):
    return None

# 【已修复】正确解析东方财富 上金所 AU9999
def parse_eastmoney(data):
    """解析东方财富返回数据"""
    try:
        price = data.get('data', {}).get('f43', 0)
        if price:
            return float(price)
    except:
        pass
    return None

# 【废弃不用，保留函数不删】
def parse_hexun(data):
    return None

def read_gist_config():
    """从 Gist 读取配置"""
    token = os.environ.get('GIST_TOKEN')
    gist_id = os.environ.get('GIST_ID')
    
    print(f"GIST_ID: {gist_id}", flush=True)
    print(f"GIST_TOKEN: {'已设置' if token else '未设置'}", flush=True)
    
    if not token or not gist_id:
        print("错误: 未设置 GIST_TOKEN 或 GIST_ID", flush=True)
        sys.exit(1)
    
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    print(f"读取 Gist: {url}", flush=True)
    resp = requests.get(url, headers=headers)
    
    if resp.status_code != 200:
        print(f"读取 Gist 失败: {resp.status_code}", flush=True)
        sys.exit(1)
    
    gist = resp.json()
    files = gist.get('files', {})
    config_file = files.get('gold_alert_config.json')
    
    if not config_file:
        print("错误: Gist 中未找到 gold_alert_config.json", flush=True)
        sys.exit(1)
    
    print("成功读取配置文件", flush=True)
    return json.loads(config_file['content'])

def update_gist_config(config):
    """更新 Gist"""
    token = os.environ.get('GIST_TOKEN')
    gist_id = os.environ.get('GIST_ID')
    
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'files': {
            'gold_alert_config.json': {
                'content': json.dumps(config, ensure_ascii=False, indent=2)
            }
        }
    }
    
    resp = requests.patch(url, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"更新 Gist 失败: {resp.status_code}", flush=True)
        return False
    return True

def send_wechat(webhook_url, message):
    """发送企业微信消息"""
    if not webhook_url:
        print("未配置企业微信 Webhook", flush=True)
        return
    
    payload = {
        "msgtype": "text",
        "text": {"content": message}
    }
    
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("推送成功", flush=True)
        else:
            print(f"推送失败: {resp.status_code}", flush=True)
    except Exception as e:
        print(f"推送异常: {e}", flush=True)

def should_alert(current_price, weighted_avg_cost, fixed_threshold, last_alert):
    """判断是否需要提醒"""
    condition1 = weighted_avg_cost > 0 and current_price < weighted_avg_cost
    condition2 = fixed_threshold > 0 and current_price < fixed_threshold
    
    if not condition1 and not condition2:
        return False, None
    
    last_price = last_alert.get('price', 0)
    last_datetime = last_alert.get('datetime', '')
    
    if abs(current_price - last_price) < 0.01:
        last_date = last_datetime[:10] if last_datetime else ''
        today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
        if last_date == today:
            print(f"今日已提醒过", flush=True)
            return False, None
    
    trigger = []
    if condition1:
        trigger.append("跌破成本价")
    if condition2:
        trigger.append("跌破固定阈值")
    
    return True, "、".join(trigger)

def get_time_label():
    now = datetime.now(BEIJING_TZ)
    return "9:30" if now.hour < 12 else "14:30"

def main():
    print("=== 黄金价格提醒任务开始 ===", flush=True)
    print(f"执行时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    if not is_trading_day():
        print("今日非交易日，任务结束", flush=True)
        return
    
    price, source = get_gold_price()
    if price is None:
        print("所有数据源均获取失败，本次任务结束", flush=True)
        return
    
    print(f"最终采用: {source}, 金价: {price} 元/克", flush=True)
    
    try:
        config = read_gist_config()
    except Exception as e:
        print(f"读取配置失败: {e}", flush=True)
        return
    
    weighted_avg_cost = config.get('weighted_avg_cost', 0)
    fixed_threshold = config.get('fixed_threshold', 1000)
    webhook_url = config.get('webhook_url', '')
    last_alert = config.get('last_alert', {'price': 0, 'datetime': ''})
    
    print(f"持仓成本: {weighted_avg_cost}, 固定阈值: {fixed_threshold}", flush=True)
    
    should_alert_flag, trigger_reason = should_alert(
        price, weighted_avg_cost, fixed_threshold, last_alert
    )
    
    config['last_price'] = {
        'price': price,
        'source': source,
        'time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if should_alert_flag:
        time_label = get_time_label()
        if weighted_avg_cost > 0:
            relation = "低于" if price < weighted_avg_cost else "高于"
            cost_text = f"{relation}你的持仓成本价 {weighted_avg_cost:.2f} 元/克"
        else:
            cost_text = "暂无持仓成本"
        
        message = f"当前金价 {price:.2f} 元/克，{cost_text} 【{time_label} 价格】"
        send_wechat(webhook_url, message)
        
        config['last_alert'] = {
            'price': price,
            'datetime': datetime.now(BEIJING_TZ).isoformat()
        }
        print(f"已发送提醒: {message}", flush=True)
    else:
        print("未触发提醒条件", flush=True)
    
    if update_gist_config(config):
        print("配置已更新", flush=True)
    else:
        print("配置更新失败", flush=True)
    
    print("=== 任务结束 ===", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"脚本执行异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)