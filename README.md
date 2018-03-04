# rosbag_fixer

Quick tool to try and work around [Message Headers missing dependency information](https://github.com/rosjava/rosjava_bootstrap/issues/16).

## Usage

```
usage: fix_bag_msg_def.py [-h] [-v] [-l] [-c CALLERID] [-m MAPPINGS]
                          inbag outbag

positional arguments:
  inbag                 Input bagfile
  outbag                Output bagfile

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Be verbose
  -l, --use-local-defs  Use message defs from local system (as opposed to
                        reading them from the provided mappings)
  -c CALLERID, --callerid CALLERID
                        Callerid (ie: publisher)
  -m MAPPINGS, --map MAPPINGS
                        Mapping topic type -> good msg def (multiple allowed)
```

## Example

### All caller ids
Replace all message definitions for all caller ids:

```
fix_bag_msg_def.py --use-local-defs /path/to/input.bag /path/to/output.bag
```

Note that definitions are only replaced when needed.

### Specific caller id
Replace all message definitions for connections with caller id `my_publisher`:

```
fix_bag_msg_def.py --use-local-defs -c '/my_publisher' /path/to/input.bag /path/to/output.bag
```
