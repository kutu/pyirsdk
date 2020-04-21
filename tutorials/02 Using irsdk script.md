When you are installing `pyirsdk` you also get `irsdk.exe` script in `X:\Python3X\Scripts` directory, which you can use for:

- Dump current iRacing memory map to binary file
	`irsdk.exe --dump data.bin`

- Parse dumped binary file to txt file
	`irsdk.exe --test data.bin --parse data.txt`

- Parse current iRacing memory map to readable txt file
	`irsdk.exe --parse data.txt`

Now, when you write your own scripts, for test purposes you can pass binary file to irsdk, instead of keeping iRacing simulator running

```python
#!python3
import irsdk
ir = irsdk.IRSDK()
ir.startup(test_file='data.bin')
print(ir['Speed'])
```

Note: `data.bin` can also be an IBT Telemetry file, use it if you need to read session data. To read IBT Telemetry samples you have to use `irsdk.IBT` Class.
