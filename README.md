# rosbag_fixer

Quick tool to try and work around [Message Headers missing dependency information](https://github.com/rosjava/rosjava_bootstrap/issues/16).

## Usage

```
usage: fix_bag_msg_def.py [-h] [-v] [-l] [-c CALLERID] [-m MAPPINGS]
                          [-t [TOPIC_PATTERNS]] [-n] [-o OUT_FOLDER]
                          inbag [inbag ...]

Attempts to fix missing or broken message definitions in ROS bags.

positional arguments:
  inbag                 Input bagfile

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Be verbose (default: False)
  -l, --use-local-defs  Use message defs from local system (as opposed to
                        reading them from the provided mappings) (default:
                        False)
  -c CALLERID, --callerid CALLERID
                        Callerid (ie: publisher) (default: None)
  -m MAPPINGS, --map MAPPINGS
                        Mapping topic type -> good msg def (multiple allowed)
                        (default: [])
  -t [TOPIC_PATTERNS], --topic [TOPIC_PATTERNS]
                        Operate only on topics matching this glob pattern
                        (specify multiple times for multiple patterns)
                        (default: [])
  -n, --no-reindex      Suppress "rosbag reindex" call (default: False)
  -o OUT_FOLDER, --out-folder OUT_FOLDER
                        Write output bagfiles to this folder." (default:
                        fixed)
```

Note that definitions are only replaced when needed.

Multiple bags can be fixed, producing one output bag per input bag. Each
output bag will have the same name as the input bag, but will be written
to the specified output folder.

## Example

### All caller ids
Replace all message definitions for all caller ids:

```
fix_bag_msg_def.py --use-local-defs /path/to/input.bag
```

### Specific caller id
Replace all message definitions for connections with caller id `my_publisher`:

```
fix_bag_msg_def.py --use-local-defs -c '/my_publisher' /path/to/input.bag
```

Note: caller ids are not necessarily equal to node or topic names.

### Specific topics

Replace message definitions for all topics that start with "/robot1/" or end with "/pose":

```
fix_bag_msg_def.py --use-local-defs -t "/robot1/*" -t "*/pose" /path/to/input.bag
```
