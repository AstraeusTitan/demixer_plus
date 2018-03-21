from kivy.metrics import sp
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, BoundedNumericProperty, AliasProperty


class ModifiedSlider(Widget):
    value = NumericProperty(0.)
    min = NumericProperty(0.)
    max = NumericProperty(0.)
    padding = NumericProperty(sp(10))
    step = BoundedNumericProperty(0, min=0)
    min_width = NumericProperty(sp(200))

    def on_min(self, *args):
        self.value = min(self.max, max(self.min, self.value))

    def on_max(self, *args):
        self.value = min(self.max, max(self.min, self.value))

    def get_norm_value(self):
        vmin = self.min
        d = self.max - vmin
        if d == 0:
            return 0
        return (self.value - vmin) / float(d)

    def set_norm_value(self, value):
        vmin = self.min
        step = self.step
        val = value * (self.max - vmin) + vmin
        if step == 0:
            self.value = val
        else:
            self.value = min(round((val - vmin) / step) * step + vmin,
                             self.max)

    value_normalized = AliasProperty(get_norm_value, set_norm_value, bind=('value', 'min', 'max', 'step'))

    def get_value_pos(self):
        padding = self.padding
        x = self.x
        y = self.y
        nval = self.value_normalized
        return x + padding + (nval * (self.width - (2 * padding))), y

    def set_value_pos(self, pos):
        padding = self.padding
        x = min(self.right - padding, max(pos[0], self.x + padding))
        if self.width == 0:
            self.value_normalized = 0
        else:
            self.value_normalized = (x - self.x - padding) / float(self.width - (2 * padding))

    value_pos = AliasProperty(get_value_pos, set_value_pos,
                              bind=('x', 'y', 'width', 'height', 'min', 'max', 'value_normalized'))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or touch.is_mouse_scrolling:
            return False
        else:
            touch.grab(self)
            self.value_pos = touch.pos
            return True

    def on_touch_move(self, touch):
        if touch.grab_current == self:
            self.value_pos = touch.pos
            return True

    def on_touch_up(self, touch):
        if touch.grab_current == self:
            self.value_pos = touch.pos
            return True
