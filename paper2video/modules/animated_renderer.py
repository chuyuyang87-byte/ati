"""Original vector-style explanatory motion graphics, rendered with Pillow."""
import math
from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from modules.card_generator import find_font,wrap_text

COLORS={'bg':'#f7f3e9','ink':'#162334','teal':'#00a895','coral':'#ef6657','gold':'#f6c44f','muted':'#697686','white':'#ffffff'}


@lru_cache(maxsize=32)
def font(size):
    return ImageFont.truetype(str(find_font()),size)


def ease(value):
    value=max(0,min(1,value));return 1-(1-value)**3


class Animator:
    """Draw in 720x1280 design coordinates; adapt to landscape separately."""
    def __init__(self,scene,profile):
        self.scene=scene;self.profile=profile
        self.width=profile['width'];self.height=profile['height']
        self.portrait=self.height>self.width
        self.events=scene.get('events',[])

    def draw(self,t,duration,caption='',caption_progress=0.0):
        portrait=self.portrait
        im=Image.new('RGB',(720,1280) if portrait else (1280,720),COLORS['bg'])
        d=ImageDraw.Draw(im)
        # Central illustration is composed at a canonical 720x760 canvas.
        art=Image.new('RGB',(720,760),COLORS['bg']);a=ImageDraw.Draw(art)
        latest=max([e['time'] for e in self.events if e['time']<=t]+[0])
        impulse=ease((t-latest)/0.6)
        p=min(1,t/max(duration,0.01))
        kind=self.scene['visual'];labels=self.scene.get('labels',['先看问题','看清机制','得到答案'])
        self.illustrate(a,kind,p,t,impulse,labels)
        if self.scene.get('summary_card'):
            summary=self.scene['summary_card']
            a.rectangle((0,0,720,760),fill=COLORS['bg'])
            self.label(a,360,80,'记住这三件事',COLORS['teal'],40)
            for i,point in enumerate(summary['points']):
                if p<i*.2:continue
                y=190+i*160
                a.rounded_rectangle((38,y,682,y+130),radius=22,fill='white')
                a.ellipse((55,y+20,95,y+60),fill=COLORS['teal'])
                a.text((75,y+24),str(i+1),font=font(23),fill='white',anchor='mt')
                for j,line in enumerate(wrap_text(point,font(29),535)):
                    a.text((115,y+23+j*41),line,font=font(29),fill=COLORS['ink'])
            for i,line in enumerate(wrap_text('学习建议：'+summary['takeaway'],font(21),650)):
                self.label(a,360,690+i*28,line,COLORS['muted'],21)
        active = [event for event in self.events if event['time'] <= t]
        if active:
            event=active[-1]
            # Timed concept badge and a focus halo appear only when the word
            # is actually spoken, using edge-tts WordBoundary timestamps.
            age=t-event['time']
            radius=int(28+15*math.exp(-age*2))
            a.ellipse((360-radius,40-radius,360+radius,40+radius),fill=COLORS['gold'])
            self.label(a,360,22,event['cue'][:12],COLORS['ink'],22)
            if event['action']=='contrast' and age<.7:
                a.line((35,80,685,80),fill=COLORS['coral'],width=max(1,int(8*(1-age/.7))))
        if portrait:
            im.paste(art,(0,245));title_y=120;title_width=640;title_size=46
            caption_y=1080;caption_width=610;caption_size=36
        else:
            im.paste(art.resize((600,633),Image.Resampling.LANCZOS),(640,40))
            title_y=170;title_width=560;title_size=44;caption_y=595;caption_width=1160;caption_size=34
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((36,42,292,88),radius=23,fill=COLORS['ink'])
        d.text((54,49),'Paper2Video / 科普',font=font(22),fill='white')
        title=self.scene.get('summary_card',{}).get('title',self.scene['title'])
        lines=wrap_text(title,font(title_size),title_width)
        offset=round((1-ease(t/0.45))*55)
        for i,line in enumerate(lines[:2]):
            d.text((40+offset,title_y+i*(title_size+13)),line,font=font(title_size),fill=COLORS['ink'])
        if not portrait:
            for i,label in enumerate(labels):
                if p>=i*.2:
                    d.rounded_rectangle((40,335+i*70,580,390+i*70),radius=16,fill='white')
                    d.text((60,345+i*70),label,font=font(28),fill=COLORS['teal'])
        if kind!='comparison':
            d.text((40,1008 if portrait else 550),'机制示意 · 非实测影像',font=font(20),fill=COLORS['muted'])
        else:
            pages=','.join(str(x['page']) for x in self.scene['citations'])
            d.text((40,1008 if portrait else 550),f'论文第{pages}页 · '+self.scene.get('metric_name','指标'),font=font(20),fill=COLORS['muted'])
        if caption:
            rows=wrap_text(caption,font(caption_size),caption_width)
            if len(rows)>2: raise ValueError('字幕超过两行，请减少单条字幕字符数')
            x=im.width//2;bottom=caption_y+len(rows)*(caption_size+11)+22
            d.rounded_rectangle((30,caption_y-15,im.width-30,bottom),radius=20,fill=COLORS['ink'])
            for i,row in enumerate(rows):
                d.text((x,caption_y+i*(caption_size+11)),row,font=font(caption_size),fill='white',anchor='mt')
            # Accent underline follows the current spoken caption interval.
            d.rounded_rectangle((50,bottom-9,50+int((im.width-100)*min(1,max(0,caption_progress)))+1,bottom-5),radius=2,fill=COLORS['gold'])
        # Continuous page-turn marker; internal motion is not limited to this bar.
        d.rectangle((0,im.height-5,int(im.width*p),im.height),fill=COLORS['teal'])
        return im.resize((self.width,self.height),Image.Resampling.LANCZOS) if im.size!=(self.width,self.height) else im

    def robot(self,d,x,y,size=1,happy=True):
        s=size
        d.rounded_rectangle((x-65*s,y-55*s,x+65*s,y+55*s),radius=int(22*s),fill=COLORS['ink'])
        for xx in [-25,25]:d.ellipse((x+(xx-9)*s,y-15*s,x+(xx+9)*s,y+3*s),fill=COLORS['teal'] if happy else COLORS['coral'])
        d.arc((x-25*s,y-3*s,x+25*s,y+32*s),0 if happy else 180,180 if happy else 360,fill='white',width=max(2,int(4*s)))
        d.line((x,y-55*s,x,y-80*s),fill=COLORS['ink'],width=max(2,int(5*s)))
        d.ellipse((x-8*s,y-91*s,x+8*s,y-75*s),fill=COLORS['gold'])

    def hospital(self,d,x,y,label,color):
        d.rounded_rectangle((x-115,y-90,x+115,y+95),radius=20,fill='white',outline=color,width=4)
        d.rectangle((x-17,y-58,x+17,y+10),fill=color);d.rectangle((x-40,y-35,x+40,y-10),fill=color)
        for xx in [-62,62]:d.rounded_rectangle((x+xx-18,y+24,x+xx+18,y+60),radius=4,fill='#dce8e4')
        d.text((x,y+112),label,font=font(27),fill=COLORS['ink'],anchor='mt')

    def arrow(self,d,start,end,color=COLORS['ink'],width=5):
        d.line((start,end),fill=color,width=width)
        angle=math.atan2(end[1]-start[1],end[0]-start[0])
        d.polygon([end,(end[0]-18*math.cos(angle-.5),end[1]-18*math.sin(angle-.5)),(end[0]-18*math.cos(angle+.5),end[1]-18*math.sin(angle+.5))],fill=color)

    def label(self,d,x,y,text,color=None,size=28):
        d.text((x,y),text,font=font(size),fill=color or COLORS['ink'],anchor='mt')

    def illustrate(self,d,kind,p,t,impulse,labels):
        if kind in {'question','domain_shift'}:
            self.hospital(d,180,170,labels[0],COLORS['teal'])
            self.hospital(d,540,170,labels[min(1,len(labels)-1)],COLORS['coral'])
            travel=ease(min(1,p*2))
            self.robot(d,180+360*travel,405+math.sin(t*2.4)*7,0.72,happy=p<.4)
            self.arrow(d,(300,160),(415,160),COLORS['muted'])
            # Identical schematic anatomy; domain color and predicted contour change.
            for x,color in [(180,COLORS['teal']),(540,COLORS['coral'])]:
                d.ellipse((x-78,510,x+78,640),fill='#d9c5ac')
                shift=0 if x==180 else 22*ease(p*2)
                d.ellipse((x-55+shift,535,x+43+shift,621),outline=color,width=7)
            self.label(d,360,675,labels[-1],COLORS['coral'] if p>.4 else COLORS['teal'],35)
            if kind=='question':
                self.label(d,360,310,'为什么？',COLORS['coral'],int(42+4*math.sin(t*4)))
        elif kind=='privacy':
            self.hospital(d,170,175,'原医院',COLORS['teal'])
            self.hospital(d,550,175,'新医院',COLORS['coral'])
            self.arrow(d,(290,175),(425,175),COLORS['muted'])
            d.arc((328,145,392,210),180,360,fill=COLORS['ink'],width=7)
            d.rounded_rectangle((320,178,400,245),radius=14,fill=COLORS['gold'])
            d.ellipse((354,195,368,209),fill=COLORS['ink'])
            self.label(d,360,320,'旧数据不能随便搬',COLORS['coral'],32)
            for i in range(3):
                x=120+i*195-20*((t*.7)%1)
                d.rounded_rectangle((x,440,x+145,570),radius=14,fill='white',outline=COLORS['teal'],width=3)
                d.ellipse((x+42,465,x+105,530),outline=COLORS['teal'],width=3)
            self.label(d,360,635,'新图片，一张张到来',COLORS['teal'],34)
        elif kind=='uncertainty':
            d.line((360,600,180,320),fill=COLORS['ink'],width=10)
            d.line((360,600,540,320),fill='#c9cfcd',width=10)
            d.rounded_rectangle((45,125,315,275),radius=22,fill=COLORS['teal'])
            d.rounded_rectangle((405,125,675,275),radius=22,fill='#c9cfcd')
            self.label(d,180,172,'看得清','white',36)
            self.label(d,540,158,'？','white',58)
            q=ease(p*1.6)
            self.robot(d,360-180*q,585-230*q,.65)
            self.label(d,360,665,'先相信，有把握的',COLORS['teal'],34)
        elif kind=='error_loop':
            centers=[(360,180),(535,410),(185,410)]
            for i,(x,y) in enumerate(centers):
                radius=65+(12*math.sin(t*3) if i==int(p*3)%3 else 0)
                d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=COLORS['coral'] if i==0 else 'white',outline=COLORS['ink'],width=3)
                self.label(d,x,y-18,labels[min(i,len(labels)-1)],'white' if i==0 else None,25)
            for i in range(3):
                start=centers[i];end=centers[(i+1)%3]
                self.arrow(d,(start[0]+(end[0]-start[0])*.3,start[1]+(end[1]-start[1])*.3),(start[0]+(end[0]-start[0])*.7,start[1]+(end[1]-start[1])*.7),COLORS['coral'])
            self.label(d,360,600,'越改，可能越错',COLORS['coral'],38)
            if any(word in self.scene.get('narration','') for word in ('闭眼','夜路','摸黑')):
                d.line([(90,555),(190,535),(290,560),(400,535),(610,560)],fill=COLORS['muted'],width=3)
                self.robot(d,100+500*p,548,.30,happy=False)
        elif kind=='graph':
            colors=[COLORS['teal'],COLORS['coral'],COLORS['gold']]
            points=[]
            q=ease(p)
            for i in range(27):
                cluster=i%3;angle=i*2.399
                start=(360+math.cos(angle)*(110+(i%5)*30),330+math.sin(angle)*(80+(i%4)*35))
                target=(180+cluster*180+math.cos(angle)*43,320+math.sin(angle)*43+(cluster==1)*110)
                points.append((start[0]*(1-q)+target[0]*q,start[1]*(1-q)+target[1]*q,cluster))
            for i,(x,y,c) in enumerate(points):
                for xx,yy,cc in points[i+1:]:
                    if c==cc and math.hypot(x-xx,y-yy)<150:
                        d.line((x,y,xx,yy),fill='#c8d6d3',width=2)
            for i,(x,y,c) in enumerate(points):
                r=11+2*math.sin(t*2+i)
                d.ellipse((x-r,y-r,x+r,y+r),fill=colors[c])
            for i,label in enumerate(labels):self.label(d,180+i*180,570,label,size=25)
            self.label(d,360,660,'相似的，聚在一起',COLORS['teal'],36)
        elif kind=='prompts':
            for i,color in enumerate([COLORS['teal'],COLORS['coral']]):
                x=180+i*360;y=160
                d.rounded_rectangle((x-120,y-70,x+120,y+70),radius=22,fill=color)
                self.label(d,x,y-20,labels[min(i,len(labels)-1)],'white',30)
                yy=250+160*((t/2+i*.3)%1)
                d.ellipse((x-9,yy-9,x+9,yy+9),fill=color)
                self.arrow(d,(x,250),(360+(i*2-1)*40,470),color)
            d.rounded_rectangle((220,470,500,610),radius=28,fill=COLORS['ink'])
            self.label(d,360,513,labels[-1],'white',32)
            self.label(d,360,670,'共性 + 差异',COLORS['teal'],36)
        elif kind=='comparison':
            metrics=self.scene['metrics'];q=ease(p*1.5)
            for i,metric in enumerate(metrics):
                y=180+i*160
                color=COLORS['teal'] if i==len(metrics)-1 else '#8b9aab'
                self.label(d,125,y-46,metric['label'],size=24)
                # Zero-to-100 scale; no truncated baseline exaggeration.
                d.rounded_rectangle((90,y,625,y+55),radius=12,fill='#e3e3df')
                end=90+535*metric['value']/100*q
                d.rounded_rectangle((90,y,max(91,end),y+55),radius=12,fill=color)
                self.label(d,575,y-47,f'{metric["value"]*q:.2f}',color,30)
            y=180+(len(metrics)-1)*160+83
            d.line((90,y,625,y),fill=COLORS['muted'],width=2)
            for value in [0,50,100]:self.label(d,90+535*value/100,y+10,str(value),COLORS['muted'],20)
            difference=metrics[-1]['value']-metrics[0]['value']
            self.label(d,360,660,f'较{metrics[0]["label"]} {difference:+.2f}个百分点',COLORS['teal'],28)
        elif kind=='boundary':
            self.robot(d,185,245,.95)
            d.line((360,120,360,530),fill=COLORS['coral'],width=9)
            d.rounded_rectangle((440,170,630,360),radius=25,fill='white',outline=COLORS['coral'],width=4)
            self.label(d,535,215,'临床部署',size=27)
            self.label(d,535,277,'还需验证',COLORS['coral'],28)
            self.arrow(d,(270,265),(330,265),COLORS['ink'])
            for i,label in enumerate(labels):
                if p>i*.2:self.label(d,360,540+i*50,label,COLORS['coral'] if i==0 else None,28)
        else:
            self.robot(d,360,210+math.sin(t*2)*6,1.15)
            for i,label in enumerate(labels):
                if p>=i*.2:
                    y=390+i*95;dx=int((1-ease(max(0,p-i*.2)*5))*60)
                    d.rounded_rectangle((90+dx,y,630+dx,y+70),radius=25,fill=COLORS['teal'] if i==0 else 'white')
                    self.label(d,360+dx,y+13,label,'white' if i==0 else None,32)


def save_story_card(scene,profile,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    Animator(scene,profile).draw(4,8).save(path)


def save_summary_card(summary,profile,path):
    scene={'title':summary['title'],'visual':'takeaway','labels':['问题','方法','边界'],
           'summary_card':summary,'citations':[]}
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    Animator(scene,profile).draw(5,8).save(path)
