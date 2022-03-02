#!/usr/bin/env python

# Copyright (c) 2018, G.A. vd. Hoorn
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Attempts to fix missing or broken message definitions in ROS bags.
"""

import argparse
import fnmatch
import os
import sys

try:
    import roslib.message
except:
    sys.stderr.write("Could not import 'roslib', make sure it is installed, "
        "and make sure you have sourced the ROS environment setup file if "
        "necessary.\n\n")
    sys.exit(1)

try:
    import rosbag
except:
    sys.stderr.write("Could not import 'rosbag', make sure it is installed, "
        "and make sure you have sourced the ROS environment setup file if "
        "necessary.\n\n")
    sys.exit(1)


def topic_matcher(topic, topic_patterns):
    if topic_patterns:
        return any([fnmatch.fnmatch(topic, p) for p in topic_patterns])
    else:
        return True


def dosys(cmd):
    sys.stderr.write(cmd + '\n')
    ret = os.system(cmd)
    if ret != 0:
        sys.stderr.write("Command failed with return value %s\n" % ret)
    return ret


def fix_bag_msg_def(
        inbag,
        out_folder,
        verbose=False,
        use_local=False,
        callerid=None,
        mappings=[],
        topic_patterns=[],
        no_reindex=False,
    ):
    if not os.path.isfile(inbag):
        sys.stderr.write('Cannot locate input bag file [%s]\n' % inbag)
        return

    outbag_path = os.path.join(out_folder, os.path.basename(inbag))

    if os.path.exists(outbag_path):
        sys.stderr.write('Not overwriting existing output file [%s]\n' % outbag_path)
        return

    # TODO: make this nicer. Figure out the complete msg text without relying on external files
    msg_def_maps = {}
    if len(mappings) > 0:
        print ("Mappings provided:")
        for mapping in mappings:
            map_msg, map_file = mapping[0].split(':')
            print ("  {:40s}: {}".format(map_msg, map_file))

            # 'geometry_msgs/PoseStamped:geometry_msgs_pose_stamped_good.txt'
            with open(map_file, 'r') as f:
                new_def = f.read()
                # skip first line, it contains something like '[geometry_msgs/PoseStamped]:'
                msg_def_maps[map_msg] = new_def.split('\n', 1)[1]
                #print (msg_def_maps[map_msg])

    else:
        if not use_local:
            print ("No mappings provided and not allowed to use local msg defs. "
                   "That is ok, but this won't fix anything like this.")

    print ("")


    # open bag to fix
    bag = rosbag.Bag(inbag)

    # filter for all connections that pass the filter expression
    # if no 'callerid' specified, returns all connections
    conxs = bag._get_connections(connection_filter=
        lambda topic, datatype, md5sum, msg_def, header:
            header['callerid'] == callerid if callerid else True)

    conxs = list(conxs)

    if not conxs:
        print ("No topics found for callerid '{}'. Make sure it is correct.\n".format(callerid))
        sys.exit(1)

    def_replaced = []
    def_not_found = []
    def_not_replaced = []

    # loop over connections, find out which msg type they use and replace
    # msg defs if needed. Note: this is a rather primitive way to approach
    # this and absolutely not guaranteed to work.
    # It does work for me though ..
    for conx in conxs:
        # skip if topic patterns were specified and this topic doesn't match
        if not topic_matcher(conx.topic, topic_patterns):
            continue

        # see if we have a mapping for that
        msg_type = conx.datatype
        if not msg_type in msg_def_maps:
            if not use_local:
                def_not_found.append((conx.topic, msg_type))
                continue

            # don't have mapping, but are allowed to use local msg def: retrieve
            # TODO: properly deal with get_message_class failing
            sys_class = roslib.message.get_message_class(msg_type)
            if sys_class is None:
                raise ValueError("Message class '" + msg_type + "' not found.")
            msg_def_maps[conx.datatype] = sys_class._full_text

        # here, we either already had a mapping or one was just created
        full_msg_text = msg_def_maps[msg_type]

        # don't touch anything if not needed (note: primitive check)
        if conx.header['message_definition'] == full_msg_text:
            def_not_replaced.append((conx.topic, msg_type))
            continue

        # here we really should replace the msg def, so do it
        conx.header['message_definition'] = full_msg_text
        conx.msg_def = full_msg_text

        def_replaced.append((conx.topic, msg_type))


    # print stats
    if def_replaced and verbose:
        print ("Replaced {} message definition(s):".format(len(def_replaced)))
        for topic, mdef in def_replaced:
            print ("  {:40s} : {}".format(mdef, topic))
        print ("")

    if def_not_replaced and verbose:
        print ("Skipped {} message definition(s) (already ok):".format(len(def_not_replaced)))
        for topic, mdef in def_not_replaced:
            print ("  {:40s} : {}".format(mdef, topic))
        print ("")

    if def_not_found and verbose:
        print ("Could not find {} message definition(s):".format(len(def_not_found)))
        for topic, mdef in def_not_found:
            print ("  {:40s} : {}".format(mdef, topic))
        print ("")



    print ("Writing out fixed bag ..")

    # write result to new bag
    # TODO: can this be done more efficiently? We only changed the connection infos.
    with rosbag.Bag(outbag_path, 'w') as outbag:
        # shamelessly copied from Rosbag itself
        meter = rosbag.rosbag_main.ProgressMeter(outbag_path, bag._uncompressed_size)
        total_bytes = 0
        for topic, raw_msg, t in bag.read_messages(raw=True):
            msg_type, serialized_bytes, md5sum, pos, pytype = raw_msg

            outbag.write(topic, raw_msg, t, raw=True)

            total_bytes += len(serialized_bytes)
            meter.step(total_bytes)

        meter.finish()

    print ("\ndone")
    cmd = "rosbag reindex %s" % outbag_path
    if no_reindex:
        print ("\nThe new bag probably needs to be re-indexed. Use '%s' for that.\n" % cmd)
    else:
        dosys(cmd)
        dosys("rm %s" % (os.path.splitext(outbag_path)[0] + ".orig.bag"))
    print("\nFixed bag at: %s" % outbag_path)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Be verbose')
    parser.add_argument('-l', '--use-local-defs', dest='use_local', action='store_true', help='Use message defs from local system (as opposed to reading them from the provided mappings)')
    parser.add_argument('-c', '--callerid', type=str, help='Callerid (ie: publisher)')
    parser.add_argument('-m', '--map', dest='mappings', type=str, nargs=1, action='append', help='Mapping topic type -> good msg def (multiple allowed)', default=[])
    parser.add_argument('-t', '--topic', dest='topic_patterns', nargs='?', help='Operate only on topics matching this glob pattern (specify multiple times for multiple patterns)', action='append', default=[])
    parser.add_argument('-n', '--no-reindex', action='store_true', help='Suppress "rosbag reindex" call', default=False)
    parser.add_argument('-o', '--out-folder', help='Write output bagfiles to this folder."', default="fixed")
    parser.add_argument('inbag', nargs='+', help='Input bagfile', default=[])
    args = parser.parse_args()

    if len(args.mappings) > 0 and args.use_local:
        sys.stderr.write("Cannot use both mappings and local defs.\n")
        sys.exit(os.EX_USAGE)

    if not os.path.isdir(args.out_folder):
        ret = dosys("mkdir -p %s" % args.out_folder)
        if ret != 0:
            sys.exit(os.EX_USAGE)

    for inbag in args.inbag:
        fix_bag_msg_def(
            inbag,
            out_folder=args.out_folder,
            verbose=args.verbose,
            use_local=args.use_local,
            callerid=args.callerid,
            mappings=args.mappings,
            topic_patterns=args.topic_patterns,
            no_reindex=args.no_reindex,
        )


if __name__ == '__main__':
    main()
