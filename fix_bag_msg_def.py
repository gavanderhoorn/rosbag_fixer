#!/usr/bin/env python

import rosbag
import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument('-v', '--verbose', action='store_true', help='Be verbose')
    parser.add_argument('-c', '--callerid', type=str, help='Callerid (ie: publisher)')
    parser.add_argument('-m', '--map', dest='mappings', type=str, nargs=1, action='append', help='Mapping topic type -> good msg def (multiple allowed)', default=[])
    parser.add_argument('inbag', help='Input bagfile')
    parser.add_argument('outbag', help='Output bagfile')
    args = parser.parse_args()

    if not os.path.isfile(args.inbag):
        sys.stderr.write('Cannot locate input bag file [%s]\n' % args.inbag)
        sys.exit(os.EX_USAGE)

    if os.path.realpath(args.inbag) == os.path.realpath(args.outbag):
        sys.stderr.write('Cannot use same file as input and output [%s]\n' % args.inbag)
        sys.exit(os.EX_USAGE)


    # TODO: make this nicer. Figure out the complete msg text without relying on external files
    msg_def_maps = {}
    if len(args.mappings) > 0:
        print ("Mappings provided:")
        for mapping in args.mappings:
            map_msg, map_file = mapping[0].split(':')
            print ("  {:40s}: {}".format(map_msg, map_file))

            # 'geometry_msgs/PoseStamped:geometry_msgs_pose_stamped_good.txt'
            with open(map_file, 'r') as f:
                new_def = f.read()
                # skip first line, it contains something like '[geometry_msgs/PoseStamped]:'
                msg_def_maps[map_msg] = new_def.split('\n', 1)[1]
                #print (msg_def_maps[map_msg])

    else:
        print ("No mappings provided. That is ok, but this won't fix anything like this.")


    print ("")


    # open bag to fix
    bag = rosbag.Bag(args.inbag)

    conxs = bag._get_connections(connection_filter=lambda topic, datatype, md5sum, msg_def, header: header['callerid'] == args.callerid)
    print ("Topics in input bag for callerid '{}':".format(args.callerid))
    for conx in conxs:
        sys.stdout.write("  {:40s} ({}): ".format(conx.topic, conx.datatype))

        # see if we have a mapping for that
        if conx.datatype in msg_def_maps:
            # we do, replace msg def
            conx.header['message_definition'] = msg_def_maps[conx.datatype]
            conx.msg_def = msg_def_maps[conx.datatype]
            print ("replaced")
        else:
            print ("no mapping found")


    print ("")


    # write result to new bag
    # TODO: can this be done more efficient? We only changed the connection infos.
    outbag = rosbag.Bag(args.outbag, 'w')
    #for topic, raw_msg, t in bag.read_messages(raw=True):
    #    outbag.write(topic, raw_msg, t, raw=True)

    print ("Writing out fixed bag ..")
    # shamelessly copied from Rosbag itself
    meter = rosbag.rosbag_main.ProgressMeter(outbag.filename, bag._uncompressed_size)
    total_bytes = 0
    for topic, msg, t in bag.read_messages(raw=True):
        msg_type, serialized_bytes, md5sum, pos, pytype = msg

        outbag.write(topic, msg, t, raw=True)

        total_bytes += len(serialized_bytes)
        meter.step(total_bytes)

    meter.finish()

    print ("done")
    print ("\nThe new bag probably needs to be re-indexed. Use 'rosbag reindex {}' for that.\n".format(outbag.filename))


if __name__ == '__main__':
    main()
