# Python iRacing SDK

Python 3 implementation of iRacing SDK can:

- Get session data (WeekendInfo, SessionInfo, etc...)
- Get live telemetry data (Speed, FuelLevel, etc...)
- Broadcast messages (camera, replay, chat, pit and telemetry commands)

# Install

- [Python 3.7+](https://www.python.org/downloads/)
- [PyYaml 5.3+](http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyyaml)
- add `X:\Python37\Scripts` directory to your `PATH` environment variable
- `pip install pyirsdk`

# Usage

```python
#!python3
import irsdk
ir = irsdk.IRSDK()
ir.startup()
print(ir['Speed'])
```

Go to [tutorials](tutorials) for more.
