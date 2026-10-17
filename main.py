# -*- coding: utf-8 -*-
"""
حاسبة الرسوم العقارية و ضريبة IRG  -  Kivy
- لا تحتاج إلى ملف fee1.kv (الواجهة كلها مكتوبة هنا)
- الخط: ضع Sahel.ttf (و Sahel-Bold.ttf إن وجد) بجانب هذا الملف
- المكتبات: pip install kivy arabic-reshaper python-bidi
"""
import os
from datetime import datetime

import arabic_reshaper

try:
    from bidi.algorithm import get_display
except ImportError:                      # python-bidi >= 0.5
    from bidi import get_display

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, Mesh, Rectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty
from kivy.resources import resource_find
from kivy.uix.behaviors import ButtonBehavior, ToggleButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex as hexc
from kivy.utils import platform


# ----------------------------------------------------------------------
#  الخط
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_font(*names):
    for n in names:
        for p in (os.path.join(BASE_DIR, n), n):
            if os.path.exists(p):
                return p
    return None


_regular = _find_font('Sahel.ttf') or resource_find('data/fonts/DejaVuSans.ttf')
_bold = _find_font('Sahel-Bold.ttf') or _regular
if _regular:
    LabelBase.register(name='custom_font', fn_regular=_regular, fn_bold=_bold)
    FONT = 'custom_font'
else:
    FONT = 'Roboto'


def ar(text):
    """تشكيل الحروف العربية و ترتيب الاتجاه لعرضها في Kivy."""
    return get_display(arabic_reshaper.reshape(text))


# ----------------------------------------------------------------------
#  النصوص (غيّر أي عنوان من هنا)
# ----------------------------------------------------------------------
T = {
    'title':        'حاسبة الرسوم العقارية',
    'subtitle':     'رسوم البيع وضريبة IRG على فائض القيمة',
    'unit':         'مليون',
    'price':        'سعر البيع (بالمليون)',
    'price_hint':   'مثال: 120',
    'tab_fees':     'الرسوم',
    'tab_irg':      'ضريبة IRG',
    'calc':         'احسب',
    'clear':        'مسح',

    'twenty':       'مبلغ الخزينة العمومية',
    'col_item':     'البند',
    'col_buyer':    'المشتري',
    'col_seller':   'البائع',
    'row_reg':      'رسوم التسجيل',
    'row_pub':      'رسوم الإشهار',
    'row_notary':   'أتعاب الموثق',
    'row_total':    'المجموع',
    'grand_total':  'المجموع الكلي',

    'buy_price':    'سعر الشراء (بالمليون)',
    'buy_hint':     'سعر الاقتناء',
    'year':         'سنة البناء',
    'year_hint':    '2005',
    'single':       'مسكن فردي',
    'collective':   'شقة ملكية وحيدة',
    'gain':         'فائض القيمة',
    'discount':     'نسبة التخفيض',
    'net':          'الوعاء الصافي',
    'tax':          'قيمة الضريبة',
}

# ----------------------------------------------------------------------
#  الألوان: أخضر صنوبري عميق + زعفران
# ----------------------------------------------------------------------
BG = hexc('#0E2623')
PANEL = hexc('#15403A')
PANEL_EDGE = hexc('#2A6358')
FIELD = hexc('#0B1D1B')
TEXT = hexc('#EAF4EF')
MUTED = hexc('#8FB3A8')
ACCENT = hexc('#F2A93B')
ACCENT_DARK = hexc('#C77F14')
INK = hexc('#10231F')
DANGER = hexc('#C8493A')
DANGER_DARK = hexc('#9C3326')
TAB_OFF = hexc('#1D554C')


# ----------------------------------------------------------------------
#  الحسابات (دوال مستقلة عن الواجهة)
# ----------------------------------------------------------------------
def calc_fees(v):
    """نفس منطق frais() الأصلي."""
    tris = round(0.2 * v, 2)
    r1 = round(v * 0.025, 2)       # المشتري
    r2 = round(v * 0.025, 2)       # البائع
    r3 = round(v * 0.01, 2)        # المشتري
    r4 = 0.0                       # البائع
    if v <= 50:
        r5 = round(v * 0.03, 2)
    elif v <= 100:
        r5 = round(50 * 0.03 + (v - 50) * 0.02, 2)
    else:
        r5 = round(50 * 0.03 + 50 * 0.02 + (v - 100) * 0.01, 2)
    r6 = 0.0
    buyer = round(r1 + r3 + r5, 2)
    seller = round(r2 + r4 + r6, 2)
    return {
        'tris': tris,
        'buyer': (r1, r5, r3, buyer),
        'seller': (r2, r6, r4, seller),
        'total': round(buyer + seller, 2),
    }


def calc_irg(sale, purchase, year, collective, now=None):
    """نفس منطق frais1() الأصلي."""
    now = now or datetime.today().year
    gain = abs(sale - purchase)
    age = now - year
    if age < 2:
        rate = 0.0
    elif age < 11:
        rate = (age - 2) * 0.05
    else:
        rate = 0.5
    net = gain - gain * rate
    tax = round(net * 0.15, 2)
    if collective:
        tax = round(tax * 0.5, 2)
    return {'gain': gain, 'rate': rate, 'net': net, 'tax': tax}


def to_num(text):
    try:
        return float(text.strip().replace(',', '.'))
    except (ValueError, AttributeError):
        return None


UNIT = ar(T['unit'])


def money(x):
    return f'{UNIT} {x:,.2f}'


# ----------------------------------------------------------------------
#  أدوات الرسم: مضلعات محدبة بزوايا مائلة
# ----------------------------------------------------------------------
def set_poly(mesh, pts):
    verts = []
    for i in range(0, len(pts), 2):
        verts += [pts[i], pts[i + 1], 0, 0]
    mesh.vertices = verts
    mesh.indices = list(range(len(pts) // 2))


def chamfer_pts(x, y, w, h, c):
    """مستطيل بزاويتين مقطوعتين بشكل مائل (أسفل اليسار و أعلى اليمين)."""
    c = max(0, min(c, w / 2.0, h / 2.0))
    return [x + c, y,
            x + w, y,
            x + w, y + h - c,
            x + w - c, y + h,
            x, y + h,
            x, y + c]


def para_pts(x, y, w, h, s):
    """متوازي أضلاع: الرؤوس مائلة بمقدار s."""
    s = max(0, min(s, w / 3.0))
    return [x + s, y, x + w, y, x + w - s, y + h, x, y + h]


def gloss_pts(x, y, w, h, s):
    """النصف العلوي من متوازي الأضلاع (لمعة خفيفة)."""
    s = max(0, min(s, w / 3.0))
    t = 0.5
    return [x + s * (1 - t), y + h * t,
            x + w - s * t, y + h * t,
            x + w - s, y + h,
            x, y + h]


# ----------------------------------------------------------------------
#  عناصر الواجهة
# ----------------------------------------------------------------------
def L(text='', shape=True, halign='right', **kw):
    """Label جاهز: خط عربي + محاذاة + منتصف عمودي."""
    kw.setdefault('font_name', FONT)
    kw.setdefault('color', TEXT)
    kw.setdefault('font_size', sp(15))
    lbl = Label(text=ar(text) if (shape and text) else text,
                halign=halign, valign='middle', **kw)
    lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
    return lbl


class Panel(BoxLayout):
    """لوحة بزوايا مائلة (أعلى اليمين و أسفل اليسار) مع ظل و حدّ."""

    def __init__(self, fill=PANEL, edge=PANEL_EDGE, cut=dp(14),
                 edge_width=1.2, **kw):
        kw.setdefault('orientation', 'vertical')
        super().__init__(**kw)
        self.cut = cut
        with self.canvas.before:
            Color(0, 0, 0, 0.32)
            self._shadow = Mesh(mode='triangle_fan')
            self._cfill = Color(*fill)
            self._body = Mesh(mode='triangle_fan')
            self._cedge = Color(*edge)
            self._line = Line(points=[0, 0, 0, 0, 0, 0], width=edge_width,
                              close=True)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def set_edge(self, rgba):
        self._cedge.rgba = rgba

    def _draw(self, *a):
        x, y = self.pos
        w, h = self.size
        set_poly(self._shadow, chamfer_pts(x, y - dp(3), w, h, self.cut))
        pts = chamfer_pts(x, y, w, h, self.cut)
        set_poly(self._body, pts)
        self._line.points = pts


class SkewButton(ButtonBehavior, Label):
    """زر بشكل متوازي أضلاع (رؤوس مائلة) مع ظل و لمعة."""
    bg = ListProperty(ACCENT)
    bg_down = ListProperty(ACCENT_DARK)
    fg = ListProperty(INK)
    fg_down = ListProperty(INK)
    skew = NumericProperty(dp(16))

    def __init__(self, **kw):
        if kw.pop('shape', True) and kw.get('text'):
            kw['text'] = ar(kw['text'])
        kw.setdefault('font_name', FONT)
        kw.setdefault('font_size', sp(17))
        kw.setdefault('bold', True)
        super().__init__(**kw)
        with self.canvas.before:
            Color(0, 0, 0, 0.38)
            self._shadow = Mesh(mode='triangle_fan')
            self._cbody = Color(*self.bg)
            self._body = Mesh(mode='triangle_fan')
            Color(1, 1, 1, 0.13)
            self._gloss = Mesh(mode='triangle_fan')
        self.bind(pos=self._draw, size=self._draw, state=self._draw,
                  bg=self._draw, bg_down=self._draw, fg=self._draw,
                  fg_down=self._draw, skew=self._draw)
        self._draw()

    def _draw(self, *a):
        x, y = self.pos
        w, h = self.size
        down = self.state == 'down'
        depth = dp(4)
        lift = 0 if down else depth
        hh = h - depth
        set_poly(self._shadow, para_pts(x, y, w, hh, self.skew))
        set_poly(self._body, para_pts(x, y + lift - (0 if down else 0), w, hh,
                                      self.skew))
        set_poly(self._gloss, gloss_pts(x, y + lift, w, hh, self.skew))
        self._cbody.rgba = self.bg_down if down else self.bg
        self.color = self.fg_down if down else self.fg
        # يرفع النص قليلاً مع الجسم
        self.padding = (0, 0, 0, 0 if down else depth)


class SkewToggle(ToggleButtonBehavior, SkewButton):
    """نسخة اختيارية (تبويب / خيار) من الزر المائل."""

    def __init__(self, **kw):
        kw.setdefault('bg', TAB_OFF)
        kw.setdefault('bg_down', ACCENT)
        kw.setdefault('fg', MUTED)
        kw.setdefault('fg_down', INK)
        kw.setdefault('font_size', sp(16))
        super().__init__(**kw)


class Field(BoxLayout):
    """عنوان صغير + حقل إدخال بزوايا مائلة."""

    def __init__(self, title, hint='', input_filter='float', **kw):
        super().__init__(orientation='vertical', size_hint_y=None,
                         height=dp(80), spacing=dp(5), **kw)
        self.add_widget(L(title, size_hint_y=None, height=dp(20),
                          color=MUTED, font_size=sp(13)))
        box = Panel(fill=FIELD, cut=dp(10), orientation='horizontal',
                    padding=[dp(12), 0], size_hint_y=None, height=dp(48))
        self.input = TextInput(
            multiline=False, input_filter=input_filter,
            hint_text=ar(hint) if hint else '', font_name=FONT,
            font_size=sp(19), halign='right',
            background_normal='', background_active='',
            background_color=(0, 0, 0, 0), foreground_color=TEXT,
            hint_text_color=(1, 1, 1, 0.25), cursor_color=ACCENT,
            selection_color=ACCENT[:3] + [0.35], write_tab=False)
        self.input.bind(size=self._pad, focus=lambda w, f: box.set_edge(
            ACCENT if f else PANEL_EDGE))
        box.add_widget(self.input)
        self.add_widget(box)

    def _pad(self, w, *a):
        py = max(0, (w.height - w.line_height) / 2.0)
        w.padding = [0, py, 0, py]


class Divider(BoxLayout):
    def __init__(self, **kw):
        super().__init__(size_hint_y=None, height=dp(1), **kw)
        with self.canvas:
            Color(*PANEL_EDGE)
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *a):
        self._r.pos, self._r.size = self.pos, self.size


def scroll_column(spacing=dp(12)):
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3), bar_color=ACCENT)
    col = GridLayout(cols=1, spacing=spacing, size_hint_y=None,
                     padding=[0, dp(4), 0, dp(8)])
    col.bind(minimum_height=col.setter('height'))
    sv.add_widget(col)
    return sv, col


def result_row(title, value='—', bold=False, big=False, color=TEXT):
    row = BoxLayout(size_hint_y=None, height=dp(34 if not big else 52))
    val = L(value, shape=False, halign='left', bold=bold or big,
            color=color, font_size=sp(21 if big else 16),
            size_hint_x=0.62 if big else 0.5, shorten=True)
    row.add_widget(val)
    name = L(title, halign='right', bold=bold,
             color=MUTED if not (bold or big) else color,
             font_size=sp(15 if not big else 17),
             size_hint_x=0.38 if big else 0.5)
    row.add_widget(name)
    return row, val, name


def table_row(item, buyer='—', seller='—', bold=False, head=False):
    row = BoxLayout(size_hint_y=None, height=dp(30 if head else 38))
    col = ACCENT if head else (TEXT if bold else TEXT)
    fs = sp(13 if head else 15)
    s_l = L(seller, shape=head, halign='center', bold=bold or head,
            color=col, font_size=fs, size_hint_x=0.28)
    b_l = L(buyer, shape=head, halign='center', bold=bold or head,
            color=col, font_size=fs, size_hint_x=0.28)
    n_l = L(item, halign='right', bold=bold or head,
            color=ACCENT if head else (TEXT if bold else MUTED),
            font_size=fs, size_hint_x=0.44, padding=(dp(4), 0))
    row.add_widget(s_l)
    row.add_widget(b_l)
    row.add_widget(n_l)
    return row, b_l, s_l


# ----------------------------------------------------------------------
#  الواجهة الرئيسية
# ----------------------------------------------------------------------
class MyWidget(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation='vertical',
                         padding=[dp(12), dp(10), dp(12), dp(10)],
                         spacing=dp(10), **kw)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.035)
            self._band = Mesh(mode='triangle_fan')
        self.bind(pos=self._draw_bg, size=self._draw_bg)
        self._draw_bg()

        self._build_header()
        self._build_price()
        self._build_tabs()
        self._build_screens()
        self.recalc()

    # ---------- خلفية ----------
    def _draw_bg(self, *a):
        self._bg.pos, self._bg.size = self.pos, self.size
        x, y = self.pos
        w, h = self.size
        set_poly(self._band, [x, y + h * 0.60, x + w, y + h * 0.80,
                              x + w, y + h, x, y + h])

    # ---------- رأس الصفحة ----------
    def _build_header(self):
        head = Panel(fill=PANEL, edge=ACCENT, cut=dp(18), size_hint_y=None,
                     height=dp(76), padding=[dp(16), dp(8)], spacing=dp(2))
        head.add_widget(L(T['title'], bold=True, color=ACCENT,
                          font_size=sp(24)))
        head.add_widget(L(T['subtitle'], color=MUTED, font_size=sp(13)))
        self.add_widget(head)

    def _build_price(self):
        self.price = Field(T['price'], T['price_hint'])
        self.price.input.bind(text=self.recalc,
                              on_text_validate=self.recalc)
        self.add_widget(self.price)

    # ---------- التبويبات ----------
    def _build_tabs(self):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8),
                        padding=[dp(6), 0])
        self.tab_irg = SkewToggle(text=T['tab_irg'], group='tabs',
                                  allow_no_selection=False)
        self.tab_fees = SkewToggle(text=T['tab_fees'], group='tabs',
                                   allow_no_selection=False, state='down')
        self._exclusive(self.tab_fees, self.tab_irg)
        self.tab_fees.bind(state=lambda w, s: s == 'down' and self._show('fees'))
        self.tab_irg.bind(state=lambda w, s: s == 'down' and self._show('irg'))
        row.add_widget(self.tab_irg)      # يظهر يسار
        row.add_widget(self.tab_fees)     # يظهر يمين
        self.add_widget(row)

    @staticmethod
    def _exclusive(a, b):
        """زران متبادلان: تفعيل أحدهما يلغي الآخر (حتى عند التغيير برمجياً)."""
        def make(other):
            def cb(w, s):
                if s == 'down' and other.state == 'down':
                    other.state = 'normal'
            return cb
        a.bind(state=make(b))
        b.bind(state=make(a))

    def _show(self, name):
        if self.sm.current == name:
            return
        self.sm.transition.direction = 'right' if name == 'fees' else 'left'
        self.sm.current = name

    # ---------- الشاشتان ----------
    def _build_screens(self):
        self.sm = ScreenManager(transition=SlideTransition(duration=0.18))

        # --- الرسوم ---
        s1 = Screen(name='fees')
        sv, col = scroll_column()

        p20 = Panel(size_hint_y=None, height=dp(56), padding=[dp(14), 0],
                    orientation='horizontal')
        self.tris = L('—', shape=False, halign='left', bold=True,
                      color=ACCENT, font_size=sp(17), size_hint_x=0.45,
                      shorten=True)
        p20.add_widget(self.tris)
        p20.add_widget(L(T['twenty'], color=MUTED, size_hint_x=0.55))
        col.add_widget(p20)

        table = Panel(size_hint_y=None, padding=[dp(12), dp(8)],
                      spacing=dp(2))
        table.bind(minimum_height=table.setter('height'))
        h, _, _ = table_row(T['col_item'], T['col_buyer'], T['col_seller'],
                            head=True)
        table.add_widget(h)
        table.add_widget(Divider())
        self.cells = []
        for key, bold in (('row_reg', False), ('row_notary', False),
                          ('row_pub', False)):
            r, b, s = table_row(T[key])
            table.add_widget(r)
            self.cells.append((b, s))
        table.add_widget(Divider())
        r, b, s = table_row(T['row_total'], bold=True)
        table.add_widget(r)
        self.cells.append((b, s))
        col.add_widget(table)

        grand = Panel(fill=PANEL, edge=ACCENT, size_hint_y=None,
                      height=dp(76), padding=[dp(16), dp(8)])
        gr, self.grand_val, _ = result_row(T['grand_total'], big=True,
                                           color=ACCENT)
        grand.add_widget(gr)
        col.add_widget(grand)

        s1.add_widget(sv)
        self.sm.add_widget(s1)

        # --- IRG ---
        s2 = Screen(name='irg')
        sv2, col2 = scroll_column()

        inputs = BoxLayout(size_hint_y=None, height=dp(80), spacing=dp(10))
        self.year = Field(T['year'], T['year_hint'], input_filter='int')
        self.buy = Field(T['buy_price'], T['buy_hint'])
        inputs.add_widget(self.year)
        inputs.add_widget(self.buy)
        for f in (self.year, self.buy):
            f.input.bind(text=self.recalc, on_text_validate=self.recalc)
        col2.add_widget(inputs)

        kinds = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8),
                          padding=[dp(6), 0])
        self.k_coll = SkewToggle(text=T['collective'], group='kind',
                                 allow_no_selection=False, font_size=sp(15))
        self.k_single = SkewToggle(text=T['single'], group='kind',
                                   allow_no_selection=False, state='down',
                                   font_size=sp(15))
        self._exclusive(self.k_single, self.k_coll)
        self.k_coll.bind(state=self.recalc)
        self.k_single.bind(state=self.recalc)
        kinds.add_widget(self.k_coll)
        kinds.add_widget(self.k_single)
        col2.add_widget(kinds)

        det = Panel(size_hint_y=None, padding=[dp(14), dp(8)],
                    spacing=dp(2))
        det.bind(minimum_height=det.setter('height'))
        r, self.v_gain, _ = result_row(T['gain'])
        det.add_widget(r)
        det.add_widget(Divider())
        r, self.v_rate, _ = result_row(T['discount'])
        det.add_widget(r)
        det.add_widget(Divider())
        r, self.v_net, _ = result_row(T['net'])
        det.add_widget(r)
        col2.add_widget(det)

        tax = Panel(fill=PANEL, edge=ACCENT, size_hint_y=None,
                    height=dp(76), padding=[dp(16), dp(8)])
        tr, self.v_tax, self.t_tax = result_row(T['tax'], big=True,
                                                color=ACCENT)
        tax.add_widget(tr)
        col2.add_widget(tax)

        s2.add_widget(sv2)
        self.sm.add_widget(s2)

        self.add_widget(self.sm)

    # ---------- الأزرار السفلية ----------
    def _build_actions(self):
        row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10),
                        padding=[dp(6), 0])
        clear = SkewButton(text=T['clear'], size_hint_x=0.4,
                           bg=DANGER, bg_down=DANGER_DARK,
                           fg=TEXT, fg_down=TEXT)
        calc = SkewButton(text=T['calc'], size_hint_x=0.6)
        clear.bind(on_release=self.clear_all)
        calc.bind(on_release=self._calc_pressed)
        row.add_widget(clear)
        row.add_widget(calc)
        self.add_widget(row)

    def _calc_pressed(self, *a):
        Window.release_all_keyboards()
        self.recalc()

    def clear_all(self, *a):
        for f in (self.price, self.buy, self.year):
            f.input.text = ''
        self.k_single.state = 'down'
        self.recalc()

    # ---------- الحساب (نفس منطق frais و frais1) ----------
    def recalc(self, *a):
        self.frais()
        self.frais1()

    def frais(self):
        v = to_num(self.price.input.text)
        if v is None:
            self.tris.text = '—'
            self.grand_val.text = '—'
            for b, s in self.cells:
                b.text = s.text = '—'
            return
        d = calc_fees(v)
        self.tris.text = money(d['tris'])
        for (b, s), bv, sv in zip(self.cells, d['buyer'], d['seller']):
            b.text = f'{bv:,.2f}'
            s.text = f'{sv:,.2f}'
        self.grand_val.text = money(d['total'])

    def frais1(self):
        sale = to_num(self.price.input.text)
        buy = to_num(self.buy.input.text)
        yr = to_num(self.year.input.text)
        collective = self.k_coll.state == 'down'
        if sale is None or buy is None or yr is None:
            self.v_gain.text = self.v_rate.text = self.v_net.text = '—'
            self.v_tax.text = '—'
            return
        d = calc_irg(sale, buy, int(yr), collective)
        self.v_gain.text = money(d['gain'])
        self.v_rate.text = f"{d['rate'] * 100:g}%"
        self.v_net.text = money(d['net'])
        self.v_tax.text = money(d['tax'])


class MyApp(App):
    title = 'IRG Calc'

    def build(self):
        Window.clearcolor = BG
        if platform in ('win', 'linux', 'macosx'):
            Window.size = (400, 760)
        else:
            Window.softinput_mode = 'below_target'
        return MyWidget()


if __name__ == '__main__':
    MyApp().run()