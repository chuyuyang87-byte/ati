"""Validate a complete render using decoded frames, audio and timing evidence."""
import json
import re
import subprocess
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from moviepy import VideoFileClip


def validate_output(folder):
    root=Path(folder);video=root/'video.mp4'
    timeline=json.loads((root/'timeline.json').read_text());script=json.loads((root/'script.json').read_text())
    executable=imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([executable,'-v','error','-i',str(video),'-f','null','-'],check=True,capture_output=True)
    raw=subprocess.run([executable,'-v','error','-i',str(video),'-t','8','-vn','-f','f32le','-ac','1','-ar','16000','pipe:1'],check=True,capture_output=True).stdout
    samples=np.frombuffer(raw,dtype='<f4');rms=float(np.sqrt(np.mean(samples*samples)))
    if rms<.01:raise ValueError('音轨近乎静音')
    captions=timeline['captions']
    if not captions or any(not 0<=c['start']<c['end']<=timeline['duration']+.01 for c in captions):raise ValueError('字幕时间边界无效')
    for scene in timeline['scenes']:
        for event in scene.get('events',[]):
            if not 0<=event['time']<scene['end']-scene['start']:raise ValueError('动作超出场景')
    article=(root/'article.md').read_text()
    for path in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',article):
        if not (root/path).is_file():raise ValueError('推文图片链接不存在')
    motion=[]
    with VideoFileClip(str(video)) as clip:
        if clip.audio is None or abs(clip.duration-timeline['duration'])>max(1,len(timeline['scenes'])*.15):raise ValueError('视频音轨或总时长异常')
        portrait=clip.h>clip.w
        for scene in timeline['scenes']:
            duration=scene['end']-scene['start']
            early=clip.get_frame(scene['start']+duration*.2)
            late=clip.get_frame(scene['start']+duration*.7)
            if portrait:early,late=early[350:950],late[350:950]
            else:early,late=early[120:520,640:1240],late[120:520,640:1240]
            changed=int(np.count_nonzero(np.abs(early.astype(int)-late.astype(int))>10))
            motion.append({'scene_id':scene['id'],'changed_diagram_pixels':changed})
        report={'duration_seconds':clip.duration,'target_seconds':script['target_seconds'],
                'resolution':list(clip.size),'scenes':len(timeline['scenes']),'captions':len(captions),
                'audio_rms_first_8_seconds':rms,'full_decode_passed':True,
                'review_model':script.get('review_model'),'review_approved':script['reviews'][-1]['approved'],
                'motion':motion,'bytes':video.stat().st_size}
    if sum(x['changed_diagram_pixels']>1000 for x in motion)<len(motion)*.7:raise ValueError('多数场景示意区域没有充分变化')
    (root/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    print(json.dumps(validate_output(a.folder),ensure_ascii=False,indent=2))
