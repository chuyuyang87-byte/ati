"""Fixed Manim templates: no execution of model-generated Python or LaTeX."""
from pathlib import Path
import math


def render_math(spec,output_dir):
    from manim import (Scene,Axes,Dot,TracedPath,Text,Create,FadeIn,Write,
                       VMobject,MoveAlongPath,tempconfig,TEAL,RED,BLACK)
    output_dir=Path(output_dir).resolve();output_dir.mkdir(parents=True,exist_ok=True)
    kind=spec.get('kind')
    if kind not in {'trajectory','formula'}:raise ValueError('仅支持trajectory或formula数学模板')
    formula=spec.get('formula','')
    points=spec.get('points',[[0,0],[1,.5],[2,1.5],[3,1]])
    if kind=='formula' and (not isinstance(formula,str) or not 1<=len(formula)<=100):raise ValueError('公式文本长度无效')
    if kind=='trajectory' and (not isinstance(points,list) or not 2<=len(points)<=100 or any(not isinstance(p,list) or len(p)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or abs(x)>100 for x in p) for p in points)):raise ValueError('轨迹点无效')
    class Explanation(Scene):
        def construct(self):
            if kind=='formula':
                # Unicode formula rendering avoids compiling arbitrary TeX.
                equation=Text(formula,font='Noto Sans CJK SC',font_size=42,color=BLACK)
                equation.scale_to_fit_width(min(10,equation.width))
                self.play(Write(equation),run_time=2)
                self.wait(2)
            else:
                xs=[p[0] for p in points];ys=[p[1] for p in points]
                axes=Axes(x_range=[min(xs)-1,max(xs)+1,1],y_range=[min(ys)-1,max(ys)+1,1],x_length=10,y_length=4,axis_config={'include_ticks':False,'color':BLACK})
                path=VMobject(color=TEAL).set_points_smoothly([axes.c2p(*p) for p in points])
                dot=Dot(axes.c2p(*points[0]),color=RED)
                trace=TracedPath(dot.get_center,stroke_color=TEAL,stroke_width=6)
                self.play(Create(axes),run_time=.5)
                self.add(trace);self.play(FadeIn(dot),run_time=.3)
                self.play(MoveAlongPath(dot,path),run_time=3)
                self.wait(.4)
    with tempconfig({'renderer':'cairo','pixel_width':720,'pixel_height':400,'frame_rate':24,
                     'background_color':'#f7f3e9','media_dir':str(output_dir),
                     'log_dir':str(output_dir/'logs'),'text_dir':str(output_dir/'texts'),
                     'disable_caching':True,'verbosity':'WARNING','progress_bar':'none'}):
        scene=Explanation();scene.render()
        return Path(scene.renderer.file_writer.movie_file_path)


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('spec',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(render_math(json.loads(a.spec.read_text()),a.output))
