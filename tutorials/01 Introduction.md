First thing you want when learning new library - shortest way to see it in action.

1. Install [pyirsdk](https://github.com/kutu/pyirsdk#install)
2. *Optional.* Install [ipython](http://www.lfd.uci.edu/~gohlke/pythonlibs/#ipython) (interactive python interpretator with autocomplete functionality)

3. *Optional.* Open `C:\Users\...\Documents\iRacing\app.ini` and change:
	```
	[Graphics]
	...
	fullScreen=0
	```

4. Go to iRacing website, and start test session with any car and with "Centripetal Circuit" (this track loads faster than others)

5. Start Python with `py` command (or `ipython` if installed in step 2.) and type:
	```python
	>>> import irsdk
	>>> ir = irsdk.IRSDK()
	>>> ir.startup()
	<<< True
	>>> ir['Speed']
	<<< 0.0
	```

When reading session data, you always must check it for existence first:

```python
>>> if ir['WeekendInfo']:
>>>     print(ir['WeekendInfo']['WeekendOptions']['StartingGrid'])
<<< '2x2 inline pole on left'
```

Most available variables (like `ir['Speed']`) with descriptions you can find [here](https://github.com/kutu/pyirsdk/blob/master/vars.txt).
