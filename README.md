# connman-mon

It's a script to monitor connection/disconnection states from connman (https://01.org/connman)
and run custom scripts on these events.

It is not ideal and not universal but it works for me and can be used as example for someone.

I use it to run some extra actions like syncing files after reconnection of
my wifi on my laptop.

Example to run:
```
some_path/connman-mon/monitor-states.py -C some_path/connman_on_postconnect.sh
```

The script uses D-Bus API provided by connman and doesn't require root access
but if your custom script for connect/disconnect actions requires root access then
this script must be run with root access as well.

For example, I added in file /etc/local.d/local.start on my laptop with Gentoo Linux
such a string:

```
start-stop-daemon --start -b --exec /some_path/connman-mon/monitor-states.py -- -C /some_path/connman_on_postconnect.sh
```

where connman_on_postconnect.sh is my custom script with actions on connect.