When you installing `pyirsdk` you also got `irsdk.exe` script in `X:\Python33\Scripts` directory, which you can use for:

- Dump current iRacing state to binary file
	`irsdk.exe --dump data.bin`

- Parse dumped binary file to txt file
	`irsdk.exe --test data.bin --parse data.txt`

- Parse current iRacing state to readable txt file
	`irsdk.exe --parse data.txt`

Now, when you write your own scripts, for test purposes you can pass binary file to irsdk, instead of keep iRacing simulator always running

```python
#!python3
import irsdk
ir = irsdk.IRSDK()
ir.startup(test_file='data.bin')
print(ir['Speed'])
```
