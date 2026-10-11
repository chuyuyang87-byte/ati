"""MoviePy rendering with Pillow Chinese captions and animated progress."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from moviepy import AudioFileClip,concatenate_audioclips,VideoClip,VideoFileClip,AudioClip,CompositeAudioClip
from modules.card_generator import find_font,wrap_text


def render_scene_card(scene,path):
    image=Image.new('RGB',(1280,720),'#111b30');draw=ImageDraw.Draw(image)
    font=str(find_font());title=ImageFont.truetype(font,48);body=ImageFont.truetype(font,36)
    title_lines=wrap_text(scene['title'],title,1120)
    if len(title_lines)>2: raise ValueError('场景标题过长')
    for i,line in enumerate(title_lines): draw.text((70,40+i*58),line,font=title,fill='white')
    y=180
    for bullet in scene['bullets']:
        lines=wrap_text('• '+bullet,body,1100)
        for line in lines:
            if y>490: raise ValueError('卡片要点过长，请缩短后重试')
            draw.text((80,y),line,font=body,fill='#dce7f5');y+=48
        y+=16
    Path(path).parent.mkdir(parents=True,exist_ok=True);image.save(path)
    return image


def make_video(timeline,output, fps=24):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype(str(find_font()),32)
    profile=timeline.get('profile',{})
    fps=profile.get('fps',fps)
    music_path=None
    if profile.get('background_music',False):
        from modules.music_generator import generate_music
        music_path=generate_music(output.parent/'music.wav',timeline['duration'])
    segment_paths=[]
    for scene in timeline['scenes']:
        path=output.parent/'cards'/f'{scene["id"]}.png'
        animator=None
        if scene.get('visual'):
            from modules.animated_renderer import Animator,save_story_card
            animator=Animator(scene,profile)
            save_story_card(scene,profile,path)
            background=None
        else:
            background=render_scene_card(scene,path)
        captions=[c for c in timeline['captions'] if scene['start']<=c['start']<scene['end']]
        readers=[];audio=None;video=None;effects=[];mixed=None;music_reader=None;math_clip=None
        try:
            readers=[AudioFileClip(p) for p in scene['audio']]
            audio=concatenate_audioclips(readers)
            if scene.get('math'):
                from modules.math_animation import render_math
                math_path=render_math(scene['math'],output.parent/'math'/scene['id'])
                math_clip=VideoFileClip(str(math_path))
            if animator and profile.get('sound_effects',False):
                for event in [{'time':0},*scene.get('events',[])]:
                    if event['time']+0.18>audio.duration:continue
                    def chime(t):
                        # An original, quiet transient; no downloaded music.
                        tt=np.asarray(t)
                        signal=0.018*np.sin(2*np.pi*(620*tt+800*tt*tt))*np.exp(-tt*28)
                        return np.column_stack((signal,signal)) if tt.ndim else np.array([signal,signal])
                    effect=AudioClip(chime,duration=.18,fps=44100).with_start(event['time'])
                    effects.append(effect)
            if music_path:
                music_reader=AudioFileClip(str(music_path))
                intervals=[(w['start'],w['end']) for w in scene.get('words',[])]
                volume=profile.get('bgm_volume',0.18)
                def music_frame(t):
                    tt=np.asarray(t)
                    signal=music_reader.get_frame(tt+scene['start'])
                    if tt.ndim:
                        speaking=np.zeros(tt.shape,dtype=bool)
                        for start,end in intervals:speaking|=(tt>=start)&(tt<=end)
                        gain=np.where(speaking,.45,1.0) if profile.get('bgm_ducking',True) else np.ones(tt.shape)
                        return signal*(gain*volume)[:,None]
                    speaking=any(start<=float(tt)<=end for start,end in intervals)
                    return signal*volume*(.45 if speaking else 1)
                effects.append(AudioClip(music_frame,duration=audio.duration,fps=44100))
            if effects:
                mixed=CompositeAudioClip([audio,*effects]).with_duration(audio.duration)
            def frame(t):
                if animator:
                    global_t=scene['start']+t
                    caption=next((c for c in captions if c['start']<=global_t<c['end']),None)
                    picture=animator.draw(t,audio.duration,
                        caption['text'] if caption else '',
                        (global_t-caption['start'])/(caption['end']-caption['start']) if caption else 0)
                    if math_clip:
                        math_time=min(math_clip.duration-1/fps,t*math_clip.duration/audio.duration)
                        panel=Image.fromarray(math_clip.get_frame(max(0,math_time)))
                        if profile['height']>profile['width']:
                            picture.paste(panel.resize((640,355)),(40,460))
                        else:
                            picture.paste(panel.resize((560,310)),(670,210))
                    return np.array(picture)
                im=background.copy();draw=ImageDraw.Draw(im)
                draw.rounded_rectangle((40,574,1240,694),radius=18,fill='#080e19')
                global_t=scene['start']+t
                caption=next((c['text'] for c in captions if c['start']<=global_t<c['end']),'')
                for i,line in enumerate(wrap_text(caption,font,1130)):
                    draw.text((640,596+i*42),line,font=font,fill='white',anchor='mt')
                draw.rectangle((0,712,int(1280*min(1,t/audio.duration)),719),fill='#43d9bd')
                return np.array(im)
            video=VideoClip(frame,duration=audio.duration).with_audio(mixed or audio)
            segment=output.parent/'segments'/f'{scene["id"]}.mp4';segment.parent.mkdir(parents=True,exist_ok=True)
            video.write_videofile(str(segment),fps=fps,codec='libx264',audio_codec='aac',preset='ultrafast',threads=2,logger=None)
            segment_paths.append(segment)
        finally:
            if video: video.close()
            if mixed: mixed.close()
            for effect in effects: effect.close()
            if audio: audio.close()
            for reader in readers: reader.close()
            if music_reader: music_reader.close()
            if math_clip: math_clip.close()
        print(f'视频片段完成：{scene["id"]}',flush=True)
    # FFmpeg stream-copy joins independently rendered MoviePy clips with bounded memory.
    import subprocess,imageio_ffmpeg
    manifest=output.parent/'segments'/'concat.txt'
    manifest.write_text(''.join("file '"+str(p.resolve()).replace("'","'\\''")+"'\n" for p in segment_paths),encoding='utf-8')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','concat','-safe','0','-i',str(manifest),'-c','copy','-movflags','+faststart',str(output)],check=True,capture_output=True)
    with VideoFileClip(str(output)) as clip:
        if clip.audio is None or abs(clip.duration-timeline['duration'])>max(1,len(segment_paths)*0.15):
            raise ValueError('最终视频音轨或时长校验失败')
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    make_video(json.loads((a.folder/'timeline.json').read_text()),a.folder/'video.mp4')
