First thing you want when learning new library - shortest way to see it in action.

1. Install [pyirsdk](https://github.com/kutu/pyirsdk#install)
2. *Optional.* Install [ipython](http://www.lfd.uci.edu/~gohlke/pythonlibs/#ipython) (interactive python interpretator with autocomplete functionality)

3. *Optional.* Open `C:\Users\...\Documents\iRacing\app.ini` and change:
	```
	[Graphics]
	...
	fullScreen=0
	```

4. Go to iRacing site, and start test session with any car and with "Centripetal Circuit" (this track loads faster than others)

5. Start `py -3` (or `ipython3` if installed in step 2.) and type:
	```python
	>>> import irsdk
	>>> ir = irsdk.IRSDK()
	>>> ir.startup()
	<<< True
	>>> ir['Speed']
	<<< 0.0
	```

Reading from yaml data, you always must check it for existence:

```python
>>> if ir['WeekendInfo']:
>>>     print(ir['WeekendInfo']['WeekendOptions']['StartingGrid'])
<<< '2x2 inline pole on left'
```

All available variables (like `ir['Speed']`) with descriptions you can find [here](https://github.com/kutu/pyirsdk/vars.txt).
