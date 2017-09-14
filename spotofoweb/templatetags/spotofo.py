
from django import template

register = template.Library()

@register.filter
def progress100(value):
  return value*100.0

