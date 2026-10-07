"""Shared validation for welcome options and previews."""
import math
DEFAULTS={'welcome_duration':2.6,'welcome_fade':True,'welcome_monitors':'all'}
def validated(options):
    duration=options.get('welcome_duration',2.6)
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or not .5<=duration<=8:raise ValueError('Welcome duration must be between 0.5 and 8 seconds.')
    monitors=options.get('welcome_monitors','all')
    if monitors not in ('all','primary'):raise ValueError('Choose all monitors or the primary monitor.')
    fade=options.get('welcome_fade',True)
    if not isinstance(fade,bool):raise ValueError('Welcome fade must be true or false.')
    return {'duration':float(duration),'fade':fade,'monitors':monitors}
