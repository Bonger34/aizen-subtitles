"""自动续跑 main.py：进程被外部回收/异常退出时自动重启，直到 25 集全部完成。

用法: python auto_resume.py
判断完成条件: subtitle/ 下存在所有 25 集的 json（按视频标题命名）。
"""
import os, sys, subprocess, time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
import params

VIDEOS_FOLDER = os.path.join(BASE, params.VIDEOS_FOLDER)
SUBTITLE_OUTPUT = os.path.join(BASE, params.SUBTITLE_OUTPUT)

def get_all_video_titles():
    """返回所有待处理视频的标题（去扩展名）"""
    titles = set()
    for f in os.listdir(VIDEOS_FOLDER):
        if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
            titles.add(os.path.splitext(f)[0])
    return titles

def get_done_titles():
    """返回已生成字幕的视频标题"""
    done = set()
    if not os.path.exists(SUBTITLE_OUTPUT):
        return done
    for f in os.listdir(SUBTITLE_OUTPUT):
        if f.endswith('.json'):
            done.add(os.path.splitext(f)[0])
    return done

def main():
    all_titles = get_all_video_titles()
    print(f"总视频: {len(all_titles)}")
    attempt = 0
    while True:
        done = get_done_titles()
        remaining = all_titles - done
        print(f"\n[轮次 {attempt+1}] 已完成 {len(done)}/{len(all_titles)}, 剩余 {len(remaining)}")
        if not remaining:
            print("=== 全部完成 ===")
            break
        attempt += 1
        # 启动 main.py，等待其退出
        py = sys.executable
        print(f"[轮次 {attempt}] 启动 main.py ...")
        proc = subprocess.run([py, os.path.join(BASE, "main.py")])
        print(f"[轮次 {attempt}] main.py 退出, code={proc.returncode}")
        # 检查是否真的完成（防死循环）
        if attempt >= 60:
            print("达到最大轮次，停止")
            break
        # 等待几秒再重启
        time.sleep(3)

if __name__ == "__main__":
    main()
