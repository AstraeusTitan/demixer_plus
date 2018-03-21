import os
from collections import namedtuple
from multiprocessing.dummy import Pool

import pyaudio
from kivy.lang import Builder
from pydub import AudioSegment
from pydub.utils import make_chunks
from kivy.app import App
from kivy.metrics import sp
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, BooleanProperty, AliasProperty, \
    BoundedNumericProperty

Builder.load_string('''
#: set base_height 20

<Container@FloatLayout>:
    size_hint: None, None

<ControlButton@Label>:
    size_hint: None, None

<ModifiedSlider>
    size_hint: None, None

<AudioControls>:
    size_hint_y: None
    height: self.vertical_padding * 2 + self.button_height
    duration: len(self.audio_chunks) * self.chunk_size if self.audio_chunks is not None else 0
    seek_time: seek_slider.value
    value_pos: seek_slider.value_pos
    value_pos_norm: seek_slider.value_normalized
    bar_start_x: seek_slider.x
    bar_end_x: seek_slider.right

    Container:
        id: playback_controls_container
        height: root.height - root.vertical_padding * 2
        width: root.horizontal_padding + (root.button_width * 3 + root.element_spacing * 2) + (root.horizontal_padding / 2)
        pos: root.x, root.y + root.vertical_padding

        ControlButton:
            id: play_button
            size: root.button_width, root.button_height
            pos: playback_controls_container.x + root.horizontal_padding, playback_controls_container.y

            canvas:
                Rectangle:
                    pos: self.pos
                    size: self.size
                    source: 'atlas://images/demixer_theme/play_button'

            on_touch_down: root.play(widget=args[0], touch=args[1])

        ControlButton:
            id: pause_button
            size: root.button_width, root.button_height
            pos: play_button.right + root.element_spacing, playback_controls_container.y

            canvas:
                Rectangle:
                    pos: self.pos
                    size: self.size
                    source: 'atlas://images/demixer_theme/pause_button'

            on_touch_down: root.pause(widget=args[0], touch=args[1])

        ControlButton:
            id: stop_button
            size: root.button_width, root.button_height
            pos: pause_button.right + root.element_spacing, playback_controls_container.y

            canvas:
                Rectangle:
                    pos: self.pos
                    size: self.size
                    source: 'atlas://images/demixer_theme/stop_button'

            on_touch_down: root.stop(widget=args[0], touch=args[1])

    Container:
        id: progressbar_container
        height: root.height - root.vertical_padding * 2
        width: root.right - self.x if root.right - self.x > seek_slider.min_width + seek_time.width + duration_time.width - root.horizontal_padding else self.x + seek_slider.min_width
        pos: playback_controls_container.right, root.y + root.vertical_padding

        Label:
            id: seek_time
            size_hint: None, None
            width: root.label_width
            height: progressbar_container.height
            text: root.milliseconds_to_display(seek_slider.value)
            pos: progressbar_container.pos

        ModifiedSlider:
            id: seek_slider
            pos: seek_time.right + root.element_spacing / 2, progressbar_container.y
            width: duration_time.x - self.x - root.element_spacing / 2
            min_width: sp(300)
            height: progressbar_container.height

            max: root.duration
            step: root.chunk_size
            value: root.seek_time

            on_touch_down: root.handle_slider_touch(widget=self, touch=args[1], touch_state='down')
            on_touch_up: root.handle_slider_touch(widget=self, touch=args[1], touch_state='up')
            on_size: self.draw_progressbar()
            on_value_pos: self.draw_progressbar()

        Label:
            id: duration_time
            size_hint: None, None
            width: root.label_width
            height: progressbar_container.height
            text: root.milliseconds_to_display(seek_slider.max)
            pos: progressbar_container.right - self.width - root.horizontal_padding, progressbar_container.y


<InputDialog>:
    BoxLayout:
        size: root.size
        pos: root.pos
        orientation: "vertical"
        FileChooserListView:
            id: filechooser
            filters: ['*.mp3', '*.wav']

        BoxLayout:
            size_hint_y: None
            height: 30
            Button:
                text: "Cancel"
                on_release: root.cancel()

            Button:
                text: "Load"
                on_release: root.load(filechooser.path, filechooser.selection)

<ExportDialog>:
    BoxLayout:
        size: root.size
        pos: root.pos
        orientation: "vertical"
        FileChooserListView:
            id: filechooser
            dirselect: True
            filters: ['*.dontshowfiles']

        BoxLayout:
            size_hint_y: None
            height: 30
            Button:
                text: "Cancel"
                on_release: root.cancel()

            Button:
                text: "Select"
                on_release: root.select(filechooser.path, filechooser.selection)

<StatusDialog>:
    Label:
        id: message
        pos: root.pos
        size: root.size
        text: root.message
        text_size: self.size
        halign: 'center'
        valign: 'middle'

<SliceControlSet>
    size_hint: None, None
    height: sp(30)
    width: label.width + timestamp.width + button.width

    Label:
        id: label
        size_hint: None, None
        width: sp(100)
        height: sp(base_height)
        text: root.label_text
        halign: 'right'
        pos: root.x, root.center_y - self.height / 2

    Label:
        id: timestamp
        size_hint: None, None
        width: sp(100)
        height: sp(base_height)
        halign: 'left'
        text_size: self.size
        pos: label.right, label.center_y - self.height / 2
        text: root.time_string

        canvas:
            Color:
                rgba: 1, 1, 1, 1
            Rectangle:
                pos: self.pos
                size: self.width, sp(1)
                source: 'atlas://images/demixer_theme/progressbar_progress'

    Label:
        id: button
        size: sp(30), sp(base_height)
        pos: timestamp.right + sp(3), timestamp.y
        text: 'Set'
        text_size: self.size
        halign: 'center'
        valign: 'middle'
        canvas.before:
            Color:
                rgba: 1, 1, 1, 1
            Rectangle:
                size: self.size
                pos: self.pos
                source: 'atlas://images/demixer_theme/blue_color_background'

        on_touch_down: root.set_time(widget=self, touch=args[1])

<SlicePreview>
    size_hint: 1, None
    height: sp(75)
    name: str(input.text)

    Label:
        id: label
        size_hint: None, None
        height: sp(30)
        width: sp(60)
        pos: root.x + sp(20), root.top - self.height
        text: 'Name: '
        text_size: self.size
        halign: 'right'
        valign: 'middle'

    TextInput:
        id: input
        text: 'Track Name'
        size_hint: None, None
        height: sp(30)
        width: remove_button.x - sp(32) - label.right
        pos: label.right, label.y
        halign: 'left'
        valign: 'middle'
        text_size: self.size
        multiline: False

    Label:
        id: remove_button
        size_hint: None, None
        size: sp(20), sp(20)
        pos: root.right - self.width, root.top - self.height
        text: 'X'
        text_size: self.size
        halign: 'center'
        valign: 'middle'

        canvas.before:
            Color:
                rgba: 1, 1, 1, 1
            Rectangle:
                size: self.size
                pos: self.pos
                source: 'atlas://images/demixer_theme/blue_color_background'

        on_touch_down: root.remove_button(widget=self, touch=args[1])

    AudioControls:
        id: controls
        width: root.width
        pos: root.pos
        audio_chunks: root.audio_chunks



<DemixerWidget>:
    canvas.before:
        Color:
            rgba: 1, 1, 1, .1
        Rectangle:
            pos: self.pos
            size: self.size

    Container:
        id: input_select_container
        height: sp(base_height)
        width: sp(500)
        x: root.center_x - self.width / 2
        y: root.top - root.top_padding - self.height

        Label:
            id: input_label
            size_hint_x: None
            width: sp(50)
            text: 'Input: '
            text_size: self.size
            halign: 'right'
            pos: input_select_container.pos

        Label:
            id: input_audio_filename
            size_hint_x: None
            pos: input_label.right, input_select_container.y
            width: show_input_dialog_button.x - self.x - sp(16)
            text: root.input_audio_filename
            text_size: self.size

            canvas:
                Color:
                    rgba: 1, 1, 1, 1
                Rectangle:
                    pos: self.pos
                    size: self.width, sp(1)
                    source: 'atlas://images/demixer_theme/progressbar_progress'

        ControlButton:
            id: show_input_dialog_button
            size: sp(20), sp(20)
            x: input_select_container.right - self.width
            center_y: input_select_container.center_y

            canvas:
                Color:
                    rgba:  1, 1, 1, 1
                Rectangle:
                    pos: self.pos
                    size: sp(21), sp(14)
                    source: 'atlas://images/demixer_theme/file_dialog_button'

            on_touch_down: root.show_dialog(widget=args[0], touch=args[1], dialog_to_display='input')

    Container:
        id: main_controls_container
        width: root.width - root.side_padding * 2
        height: sp(220)
        pos: root.x + root.side_padding, input_select_container.y - self.height - sp(32)

        Label:
            id: audio_status_label
            text: root.audio_status
            text_size: self.size
            halign: 'left'
            size_hint: None, None
            height: sp(base_height)
            width: sp(300)
            pos: main_controls_container.x + main_controls.horizontal_padding, main_controls_container.top - self.height

        AudioControls:
            id: main_controls
            audio_chunks: root.audio_chunks
            chunk_size: root.chunk_size
            pos: main_controls_container.x, audio_status_label.y - self.height - sp(10)

        SliceControlSet:
            id: start_slice_controls
            pos: root.center_x - self.width / 2 - sp(16), main_controls.y - self.height - sp(16)
            time: main_controls.seek_time
            label_text: 'Slice start: '

        SliceControlSet:
            id: end_slice_controls
            pos: root.center_x - self.width / 2 - sp(16), start_slice_controls.y - self.height - sp(16)
            time: main_controls.seek_time
            label_text: 'Slice end: '

        SliceIndicator:
            id: slice_start_indicator
            visible: start_slice_controls.slice_time_set
            size_hint: None, None
            size: sp(9), sp(20)
            home_pos: main_controls.bar_start_x - self.width, main_controls.center_y - self.height - sp(5)
            mark_pos: main_controls.value_pos[0] - self.width / 2, main_controls.center_y - self.height - sp(5)
            image_path: 'atlas://images/demixer_theme/slice_indicator_start'

        SliceIndicator:
            id: slice_end_indicator
            visible: end_slice_controls.slice_time_set
            size_hint: None, None
            size: sp(9), sp(20)
            home_pos: main_controls.bar_end_x - self.width, main_controls.center_y - self.height - sp(5)
            mark_pos: main_controls.value_pos[0] - self.width / 2, main_controls.center_y - self.height - sp(5)
            image_path: 'atlas://images/demixer_theme/slice_indicator_end'

        Label:
            id: save_button
            size_hint: None, None
            size: sp(64), sp(base_height)
            pos: main_controls_container.center_x - self.width / 2, end_slice_controls.y - self.height - sp(10)
            text:'Save'
            text_size: self.size
            halign: 'center'

            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                Rectangle:
                    size: self.size
                    pos: self.pos
                    source: 'atlas://images/demixer_theme/blue_color_background'

            on_touch_down: root.save_button(widget=self, touch=args[1], start=start_slice_controls.stored_time, end=end_slice_controls.stored_time)

    SliceListDisplay:
        grid: slice_list
        id: slice_display
        do_scroll_x: False
        size_hint: None, None
        width: root.width - root.side_padding * 2
        height: main_controls_container.y - export_select_container.y - sp(10)
        pos: root.x + root.side_padding, export_select_container.top + sp(10)

        GridLayout:
            id: slice_list
            cols: 1
            spacing: sp(0)
            padding: sp(0)
            size_hint_y: None
            height: slice_list.height
            pos: slice_list.pos

    Container:
        id: export_select_container
        height: sp(base_height)
        width: sp(500)
        pos: root.center_x - self.width / 2, export_controls.top +sp(5)

        Label:
            id: export_label
            size_hint_x: None
            width: sp(75)
            text: 'Export to: '
            text_size: self.size
            halign: 'right'
            valign: 'middle'
            pos: export_select_container.pos

        Label:
            id: export_dir_name
            size_hint_x: None
            pos: export_label.right, export_select_container.y
            width: show_export_dialog_button.x - self.x - sp(16)
            text: root.export_path
            text_size: self.size

            canvas:
                Color:
                    rgba: 1, 1, 1, 1
                Rectangle:
                    pos: self.pos
                    size: self.width, sp(1)
                    source: 'atlas://images/demixer_theme/progressbar_progress'

        ControlButton:
            id: show_export_dialog_button
            size: sp(20), sp(20)
            x: export_select_container.right - self.width
            center_y: export_select_container.center_y

            canvas:
                Color:
                    rgba:  1, 1, 1, 1
                Rectangle:
                    pos: self.pos
                    size: sp(21), sp(14)
                    source: 'atlas://images/demixer_theme/file_dialog_button'

            on_touch_down: root.show_dialog(widget=args[0], touch=args[1], dialog_to_display='export')

    Container:
        id: export_controls
        size_hint: None, None
        width: root.width - root.side_padding * 2
        height: sp(40)
        pos: root.x + root.side_padding, root.y + root.bottom_padding

        Label:
            id: export_button
            size_hint: None, None
            size: sp(64), sp(base_height)
            pos: export_controls.center_x - self.width / 2, export_controls.top - self.height
            text: 'Export'
            text_size: self.size
            halign: 'center'
            valign: 'middle'

            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                Rectangle:
                    size: self.size
                    pos: self.pos
                    source: 'atlas://images/demixer_theme/blue_color_background'

            on_touch_down: root.export_button(widget=self, touch=args[1])

        Label:
            id: export_status_label
            size_hint: 1, None
            height: sp(base_height)
            text: root.export_status
            text_size: self.size
            halign: 'center'
            valign: 'middle'
            pos: export_controls.pos
''')


# Start of modified_slider.py
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

    def draw_progressbar(self):
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=(self.x + self.padding, self.center_y - sp(2.5)),
                      size=(self.width - self.padding * 2, sp(6)),
                      source='atlas://images/demixer_theme/progressbar_background')
            Rectangle(pos=(self.x + self.padding, self.center_y - sp(2.5)),
                      size=(self.value_pos[0] - self.x, sp(6)),
                      source='atlas://images/demixer_theme/progressbar_progress')
            Rectangle(pos=(self.value_pos[0] - sp(10.5), self.center_y - sp(10.5)),
                      size=(sp(21), sp(21)),
                      source='atlas://images/demixer_theme/progressbar_knob')


# Start of audio_controls.py
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


# Start of original demixer.pyw
class InputDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class ExportDialog(FloatLayout):
    select = ObjectProperty(None)
    cancel = ObjectProperty(None)


class StatusDialog(FloatLayout):
    message = StringProperty('')


class SliceIndicator(Widget):
    home_pos = ObjectProperty((0, 0))
    mark_pos = ObjectProperty((0, 0))
    current_pos = ObjectProperty((0, 0))
    image_path = StringProperty('')
    visible = BooleanProperty(False)

    def on_visible(self, instance, value):
        self.current_pos = self.mark_pos
        if value:
            self.show()
        else:
            self.hide()

    def clear(self):
        self.canvas.clear()

    def show(self):
        self.pos = self.current_pos
        self.clear()
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size, source=self.image_path)

    def hide(self):
        self.clear()
        self.pos = self.home_pos

    def on_mark_pos(self, instance, value):
        self.current_pos = self.current_pos[0], value[1]
        if self.visible:
            self.show()
        else:
            self.hide()


class SliceControlSet(Widget):
    label_text = StringProperty('')
    time = NumericProperty(0)
    stored_time = NumericProperty(0)
    time_string = StringProperty('')
    slice_time_set = BooleanProperty(False)

    @staticmethod
    def timestamp_to_milliseconds(timestamp):
        parts = str.split(timestamp, ':')
        seconds = parts.pop()
        while seconds == '' and len(parts) > 0:
            seconds = parts.pop()
        if '.' in seconds:
            seconds = str.split(seconds, '.')

        millisec = int(seconds[0]) * 1000
        if len(seconds) > 1 and seconds[1] != '':
            millisec += int(seconds[1]) * 100
        if parts:
            millisec += int(parts.pop()) * 60 * 1000
        if parts:
            millisec += int(parts.pop()) * 60 * 60 * 1000
        return int(millisec)

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

    def set_time(self, widget, touch):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling:
            return
        else:
            self.slice_time_set = False
            self.stored_time = self.time
            self.time_string = self.milliseconds_to_display(self.time)
            self.slice_time_set = True

    def reset(self):
        self.slice_time_set = False
        self.time = 0
        self.stored_time = self.time
        self.time_string = self.milliseconds_to_display(self.time)


class SlicePreview(Widget):
    audio_chunks = ObjectProperty()
    start_time = NumericProperty(0)
    start_chunk = NumericProperty(0)
    end_time = NumericProperty(0)
    end_chunk = NumericProperty(0)
    name = StringProperty('')

    def remove_button(self, widget, touch):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling:
            return False
        else:
            self.remove()

    def remove(self):
        self.ids.controls.stop_playback()
        self.parent.remove_widget(self)

    def on_name(self, instance, value):
        if str.endswith(str(value), '.mp3'):
            return
        else:
            self.name = str(value) + '.mp3'


class SliceListDisplay(ScrollView):
    grid = ObjectProperty()

    def on_grid(self, instance, grid):
        grid.bind(minimum_height=grid.setter('height'))


class DemixerWidget(Widget):
    _pool = Pool(processes=1)

    min_width = NumericProperty(sp(600))
    top_padding = NumericProperty(sp(32))
    bottom_padding = NumericProperty(sp(16))
    side_padding = NumericProperty(sp(16))

    audio_status = StringProperty('Status: Select a file')
    export_status = StringProperty('Export status: Select an export destination')

    audio_path = StringProperty('')
    _base_audio = None
    input_audio_filename = StringProperty('')
    _audio_file_type = ''
    _input_audio_chunks = None
    audio_chunks = ObjectProperty(_input_audio_chunks)
    chunk_size = NumericProperty(100)

    Slice = namedtuple('Slice', ['name', 'start_time', 'end_time', 'start_chunk', 'end_chunk'])
    list_of_slices = []

    export_path = StringProperty('')

    def reset_main_controls(self):
        self.ids.start_slice_controls.reset()
        self.ids.end_slice_controls.reset()
        self.ids.main_controls.reset()

    def set_audio_path(self, path):
        self.audio_path = str(path)
        self.input_audio_filename = os.path.basename(self.audio_path)
        ext = str.split(self.input_audio_filename, '.')[-1]
        self._audio_file_type = ext
        self.reset_main_controls()

    def load_audio(self):
        self._pool.apply_async(self.async_audio_load)

    def async_audio_load(self):
        self.audio_status = 'Status: Audio is Loading'
        self._base_audio = AudioSegment.from_file(self.audio_path, self._audio_file_type)
        self._input_audio_chunks = make_chunks(self._base_audio, self.chunk_size)
        self.audio_chunks = self._input_audio_chunks
        self.audio_status = 'Status: Ready'

    def dismiss_dialog(self):
        self._popup.dismiss()

    def show_dialog(self, widget, touch, dialog_to_display):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling:
            return False
        else:
            if dialog_to_display == 'input':
                self.show_input_dialog()
            elif dialog_to_display == 'export':
                self.show_export_dialog()
        return True

    def show_input_dialog(self):
        content = InputDialog(load=self.select_input_file, cancel=self.dismiss_dialog)
        self._popup = Popup(title='Select audio file',
                            content=content,
                            size_hint=(.5, .5))
        self._popup.open()

    def show_export_dialog(self):
        content = ExportDialog(select=self.select_export_dir, cancel=self.dismiss_dialog)
        self._popup = Popup(title='Select export folder',
                            content=content,
                            size_hint=(.5, .5))
        self._popup.open()

    def show_status_dialog(self, message):
        content = StatusDialog(message=message)
        self._popup = Popup(title='Status',
                            content=content,
                            size_hint=(.4, .2))
        self._popup.open()

    def select_input_file(self, path, filename):
        self.dismiss_dialog()
        if filename:
            if self.has_slice():
                self.show_status_dialog('You have created slices. Export them before selecting a new input file')
            else:
                self.set_audio_path(filename[0])
                self.load_audio()

    def select_export_dir(self, path, filename):
        self.dismiss_dialog()
        if filename:
            self.export_path = str(filename[0])
            self.export_status = ''

    def save_button(self, widget, touch, start, end):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling or not self._input_audio_chunks:
            return False
        else:
            self.save_slice(start=int(start), end=int(end))

    def save_slice(self, start, end):
        grid = self.ids.slice_list
        start_chunk = int(start / self.chunk_size)
        end_chunk = int(end / self.chunk_size)
        audio_chunks = self._input_audio_chunks[start_chunk:end_chunk]
        grid.add_widget(SlicePreview(audio_chunks=audio_chunks,
                                     start_time=start,
                                     end_time=end,
                                     start_chunk=start_chunk,
                                     end_chunk=end_chunk))

    def export_button(self, widget, touch):
        if not Widget.collide_point(widget, *touch.pos) or touch.is_mouse_scrolling \
                or not self._input_audio_chunks or not self.has_slice():
            return False
        else:
            self.export_status = 'Beginning export'
            self.export_slices()

    def has_slice(self):
        if self.ids.slice_list.children:
            return True
        else:
            return False

    def export_slices(self):
        if not self.has_slice():
            return
        previews = self.ids.slice_list.children
        slices = self.list_of_slices
        self.export_status = 'Building list of slices'
        for preview in previews:
            audio_slice = self.Slice(name=preview.name,
                                     start_time=preview.start_time,
                                     start_chunk=preview.start_chunk,
                                     end_time=preview.end_time,
                                     end_chunk=preview.end_chunk)
            self.export_status = 'Added: ' + str(audio_slice.name) + ' duration: ' + \
                                 self.milliseconds_to_display(audio_slice.end_time - audio_slice.start_time)
            slices.append(audio_slice)
        self.export_status = 'Export ' + str(len(slices)) + ' slices to file'
        self._pool.apply_async(self.save_slices_to_file_async, callback=self.clear_slices)

    def clear_slices(self, *args):
        self.list_of_slices = []
        for preview in self.ids.slice_list.children:
            preview.parent.remove_widget(preview)

    def save_slices_to_file_async(self):
        for audio_slice in self.list_of_slices:
            name = str(audio_slice.name)
            export_name = os.path.join(self.export_path, name)
            start = audio_slice.start_time
            end = audio_slice.end_time
            self.export_status = 'Exporting: ' + name
            self._base_audio[start:end].export(export_name, format='mp3')
            self.export_status = 'Finished export: ' + name
        self.export_status = 'Finished exporting ' + str(len(self.list_of_slices)) + ' tracks'
        self.list_of_slices = []

    @staticmethod
    def timestamp_to_millisec(timestamp):
        parts = str.split(timestamp, ':')
        millisec = float(parts.pop()) * 1000
        if parts:
            millisec += float(parts.pop()) * 60 * 1000
        if parts:
            millisec += float(parts.pop()) * 60 * 60 * 1000
        return millisec

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


class DemixerApp(App):
    def build(self):
        self.icon = 'demixer_icon.png'
        return DemixerWidget()


if __name__ == '__main__':
    DemixerApp().run()
