#!/usr/bin/python3
"""Reproducible Cairo source for the original session/boot artwork."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'assets/session'))
from visuals import png,login,boot,background,brand
png(root/'assets/session/login.png',1920,1080,login)
for i in range(48):
    for prefix in ('throbber','animation'):
        png(root/'assets/boot'/f'{prefix}-{i+1:04}.png',640,360,lambda c,w,h,n=i:boot(c,w,h,n))
print('Generated login art and 48-frame blue-bar boot animation.')

def shutdown(c,w,h):
    background(c,w,h);brand(c,w/2-151,h*.40,1.2)
png(root/'assets/shutdown/background.png',1920,1080,shutdown)

def installer_logo(c,w,h):
    import cairo
    options=cairo.FontOptions();options.set_antialias(cairo.ANTIALIAS_GRAY);c.set_font_options(options)
    brand(c,5,2,.93)
png(root/'assets/session/installer-logo.png',240,85,installer_logo)
