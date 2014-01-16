# Python iRacing SDK

Python 3 implementation of iRacing SDK can:

- Get YAML data (WeekendInfo, SessionInfo)
- Get variable data (Speed, FuelLevel)
- Broadcast messages (chat, pit, replay commands)

# Install

- [Python 3.3+](http://www.python.org/download/)
- [setuptools 2.0.2+](http://www.lfd.uci.edu/~gohlke/pythonlibs/#setuptools)
- [PyYaml 3.10+](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyyaml)
- [pip 1.5+](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pip)
- add `X:\Python33\Scripts` directory to your `PATH` environment variable
- `pip3 install pyirsdk`

# Usage

```python
#!python3

import irsdk

ir = irsdk.IRSDK()
ir.startup()

print(ir['Speed'])
```

Go to [tutorials](tutorials) for more.
