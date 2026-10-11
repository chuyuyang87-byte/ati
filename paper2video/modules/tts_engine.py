"""Whole-scene edge-tts with word timings, cue events and content-addressed cache."""
import argparse
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
import edge_tts
import edge_tts.communicate as edge_communicate
from moviepy import AudioFileClip
from config import load_settings


def sentences(text):
    return [part for part in re.findall(r'.{1,26}(?:[，。！？；!?;]|$)|.{1,26}',text.replace('\n','')) if part.strip()]


def timestamp(seconds):
    milliseconds=round(seconds*1000)
    h,remainder=divmod(milliseconds,3600000);m,remainder=divmod(remainder,60000);s,ms=divmod(remainder,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def write_srt(captions,path):
    Path(path).write_text('\n\n'.join(f'{i}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}' for i,c in enumerate(captions,1))+'\n',encoding='utf-8')


def normalize(text):
    return ''.join(c.casefold() for c in text if c.isalnum())


def group_words(words,max_chars=18):
    groups=[];current=[]
    for word in words:
        if len(word['text'])>max_chars:
            raise ValueError('TTS返回单词过长，无法显示字幕')
        if current and (sum(len(w['text']) for w in current)+len(word['text'])>max_chars or word['end']-current[0]['start']>3.5):
            groups.append({'start':current[0]['start'],'end':current[-1]['end'],'text':''.join(w['text'] for w in current)})
            current=[]
        current.append(word)
    if current:groups.append({'start':current[0]['start'],'end':current[-1]['end'],'text':''.join(w['text'] for w in current)})
    return groups


def cue_events(beats,words):
    joined=''.join(normalize(w['text']) for w in words)
    events=[]
    for beat in beats:
        cue=normalize(beat['cue']);index=joined.find(cue)
        if index<0:raise ValueError('配音中找不到动作触发词：'+beat['cue'])
        position=0
        for word in words:
            length=len(normalize(word['text']))
            if position+length>index:
                events.append({**beat,'time':word['start']});break
            position+=length
    return sorted(events,key=lambda event:event['time'])


async def synthesize(script,output_dir):
    folder=Path(output_dir);folder.mkdir(parents=True,exist_ok=True)
    settings=load_settings();captions=[];scenes=[];cursor=0.0
    profile=script.get('profile',{})
    rate=profile.get('voice_rate','+0%');max_chars=profile.get('max_caption_chars',26)
    ca_bundle=os.getenv('SSL_CERT_FILE')
    if ca_bundle:edge_communicate._SSL_CTX.load_verify_locations(cafile=ca_bundle)
    for scene in script['scenes']:
        text=scene['narration']
        key=hashlib.sha256(json.dumps([text,settings.tts_voice,rate,'WordBoundary'],ensure_ascii=False).encode()).hexdigest()[:20]
        path=folder/f'{key}.mp3';metadata=folder/f'{key}.json'
        words=None
        if path.is_file() and metadata.is_file():
            words=json.loads(metadata.read_text())['words']
        else:
            for attempt in range(3):
                temporary=path.with_suffix('.part.mp3');words=[]
                try:
                    communicate=edge_tts.Communicate(text,settings.tts_voice,rate=rate,boundary='WordBoundary',proxy=os.getenv('HTTPS_PROXY') or os.getenv('https_proxy'))
                    async def receive():
                        with temporary.open('wb') as stream:
                            async for chunk in communicate.stream():
                                if chunk['type']=='audio':stream.write(chunk['data'])
                                elif chunk['type']=='WordBoundary':
                                    start=chunk['offset']/10_000_000
                                    words.append({'start':start,'end':start+chunk['duration']/10_000_000,'text':chunk['text']})
                    await asyncio.wait_for(receive(),timeout=120)
                    if not words:raise ValueError('TTS没有返回单词时间戳')
                    with AudioFileClip(str(temporary)) as clip:
                        if clip.duration<=0:raise ValueError('配音为空')
                    temporary.replace(path)
                    metadata.write_text(json.dumps({'words':words},ensure_ascii=False),encoding='utf-8')
                    break
                except Exception:
                    temporary.unlink(missing_ok=True)
                    if attempt==2:raise
                    await asyncio.sleep(1+attempt)
        with AudioFileClip(str(path)) as clip:duration=clip.duration
        if not words or any(not 0<=w['start']<w['end']<=duration+0.2 for w in words):
            raise ValueError('TTS时间戳超出实际音频边界')
        # Clamp sub-frame encoder rounding at the last word only.
        words=[{**w,'end':min(w['end'],duration)} for w in words]
        for caption in group_words(words,max_chars):
            captions.append({**caption,'scene_id':scene['id'],'start':cursor+caption['start'],'end':cursor+caption['end']})
        scenes.append({**scene,'start':cursor,'end':cursor+duration,'audio':[str(path.resolve())],
                       'words':words,'events':cue_events(scene.get('beats',[]),words)})
        cursor+=duration
        print(f'配音完成：{scene["id"]}（{duration:.1f}秒，词级时间戳）',flush=True)
    timeline={'duration':cursor,'scenes':scenes,'captions':captions,'profile':profile}
    write_srt(captions,folder.parent/'subtitles.srt')
    (folder.parent/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    return timeline


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    asyncio.run(synthesize(json.loads((a.folder/'script.json').read_text()),a.folder/'audio'))
