from kivy.metrics import sp
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.uix.widget import Widget
import pyaudio
from multiprocessing.dummy import Pool


class AudioControls(Widget):
    vertical_padding = NumericProperty(sp(10))
    horizontal_padding = NumericProperty(sp(32))
    element_spacing = NumericProperty(sp(16))

    label_width = NumericProperty(sp(80))
    text_height = NumericProperty(sp(10))

    button_width = NumericProperty(sp(20))
    button_height = NumericProperty(sp(20))

    bar_start_x = NumericProperty()
    bar_end_x = NumericProperty()

    duration = NumericProperty(0)
    seek_time = NumericProperty(0)
    value_pos = ObjectProperty(None)
    value_pos_norm = NumericProperty(0.)

    _audio_chunks = None
    audio_chunks = ObjectProperty(_audio_chunks)
    chunk_size = NumericProperty(100)

    playback_state = StringProperty('stopped')
    pa = None
    stream = None

    pool = Pool(processes=1)

    def __init__(self, **kwargs):
        super(AudioControls, self).__init__(**kwargs)

    def reset(self):
        self.seek_time = 0
        self.playback_state = 'stopped'

    def on_audio_chunks(self, instance, value):
        self._audio_chunks = value

    def handle_slider_touch(self, widget, touch, touch_state):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling:
            return False
        else:
            if touch_state == 'down' and self.playback_state == 'playing':
                self.playback_state = 'paused'
            elif touch_state == 'up' and self.playback_state == 'paused':
                self.playback_state = 'playing'
                self.play(widget, touch)
        return True

    def play_chunks(self):
        i = int(self.seek_time / self.chunk_size)
        chunks = self._audio_chunks
        while i < len(chunks):
            chunk = chunks[i]
            if self.stream is None:
                self.playback_state == 'stopped'
                return
            if self.playback_state == 'playing':
                self.stream.write(chunk.raw_data)
                self.seek_time += self.chunk_size
                i += 1
            else:
                break
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        self.stream = None
        return

    def play(self, widget, touch):
        if not Widget.collide_point(widget, *touch.pos) or self._audio_chunks is None or touch.is_mouse_scrolling:
            return False
        else:
            seg = self._audio_chunks[0]
            self.pa = pyaudio.PyAudio()
            if self.stream is not None:
                self.playback_state = 'playing'
                return True
            self.stream = self.pa.open(format=self.pa.get_format_from_width(seg.sample_width),
                                       channels=seg.channels,
                                       rate=seg.frame_rate,
                                       output=True)
            self.playback_state = 'playing'
            self.pool.apply_async(self.play_chunks)
        return True

    def pause(self, widget, touch):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling:
            return False
        elif self.playback_state == 'playing':
            self.playback_state = 'paused'
        return True

    def stop(self, widget, touch):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling:
            return False
        else:
            self.playback_state = 'stopped'
            self.seek_time = 0
        return True

    def stop_playback(self):
        self.playback_state = 'stopped'

    @staticmethod
    def milliseconds_to_display(value):
        seconds = value / 1000.0
        if seconds < 60:
            return '%02d:%02d:%02.1f' % (0, 0, seconds)
        minutes = int(seconds / 60)
        seconds %= 60
        if minutes < 60:
            return '%02d:%02d:%02.1f' % (0, minutes, seconds)
        hours = int(minutes / 60)
        minutes %= 60
        return '%02d:%02d:%02.1f' % (hours, minutes, seconds)


if __name__ == '__main__':
    from kivy.app import App


    class AudioControlsApp(App):
        def build(self):
            return AudioControls()


    AudioControlsApp().run()
