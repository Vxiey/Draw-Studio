from pathlib import Path

p=Path('ExecutionCostModel.py')
text=p.read_text(encoding='utf-8')
start=text.find('\n@property\ndef scale_x')
end=text.find('\n    def path_cost(', start if start >= 0 else 0)
if start < 0 or end < 0:
    raise SystemExit('rc19 malformed compatibility block not found')
compat='''
    @property
    def scale_x(self) -> float:
        return float(self.sx)

    @property
    def scale_y(self) -> float:
        return float(self.sy)

    @property
    def path_fixed_seconds(self) -> float:
        base=(self.travel_wait + float(self.delivery.press_settle) +
              float(self.delivery.release_settle) + self.boundary_wait + .0015)
        return max(.000001,base*self.multiplier)

    @property
    def learned_path_floor_seconds(self) -> float:
        values=[]
        for kind in ("short_stroke","long_stroke","stroke","path"):
            value=self._learned_average(kind,0.0)
            if value>0:values.append(float(value))
        return max(0.0,min(values)*self.multiplier) if values else 0.0

    @property
    def draw_seconds_per_px(self) -> float:
        return max(1e-12,(self.path_wait/max(.5,float(self.delivery.step_px)))*self.multiplier)

    @property
    def color_change_seconds(self) -> float:
        return float(self.switch_cost("palette_change"))

    @property
    def model_version(self) -> int:
        return EXECUTION_MODEL_VERSION

    @property
    def calibration_confidence(self) -> float:
        if self.samples<=0:return 0.0
        return max(0.0,min(.95,1.0-math.exp(-float(self.samples)/4.0)))

    @property
    def uncertainty_multiplier(self) -> float:
        if self.samples<=0:return 1.0
        return 1.0+(1.0-self.calibration_confidence)*.10

    def path_seconds(self,path: Sequence[Point],*,cursor: Point|None=None,brush_px: int|None=None) -> float:
        return float(self.path_cost(path,cursor=cursor,brush_px=brush_px).total_seconds)

    def paths_seconds(self,paths: Iterable[Sequence[Point]],*,cursor: Point|None=None,brush_px: int|None=None) -> float:
        total=0.0;current=cursor
        for path in paths or ():
            if not path:continue
            total+=self.path_seconds(path,cursor=current,brush_px=brush_px)
            current=tuple(map(int,path[-1]))
        return total

    def risk_adjusted_seconds(self,seconds: float) -> float:
        value=max(0.0,float(seconds or 0.0))
        return value*self.uncertainty_multiplier

    def as_dict(self) -> dict[str,Any]:
        return {
            "model":"ExecutionCostModel","model_version":self.model_version,"source":self.source,
            "samples":self.samples,"scale_x":round(self.scale_x,7),"scale_y":round(self.scale_y,7),
            "path_fixed_seconds":round(self.path_fixed_seconds,7),
            "draw_seconds_per_px":round(self.draw_seconds_per_px,9),
            "color_change_seconds":round(self.color_change_seconds,7),
            "calibration_confidence":round(self.calibration_confidence,7),
            "uncertainty_multiplier":round(self.uncertainty_multiplier,7),
        }
'''
p.write_text(text[:start]+'\n'+compat+text[end:],encoding='utf-8')
