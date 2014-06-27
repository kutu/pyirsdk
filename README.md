# Python iRacing SDK

Python 3 implementation of iRacing SDK can:

- Get session data (WeekendInfo, SessionInfo, etc...)
- Get telemetry data (Speed, FuelLevel, etc...)
- Broadcast messages (camera, replay, chat, pit and telemetry commands)

# Install

- [Python 3.3+](http://www.python.org/download/)
- [setuptools 2.0.2+](http://www.lfd.uci.edu/~gohlke/pythonlibs/#setuptools) _(no need for Python 3.4+)_
- [PyYaml 3.11+](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyyaml)
- [pip 1.5+](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pip) _(no need for Python 3.4+)_
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
