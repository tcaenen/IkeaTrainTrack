import argparse
import collections
import os
import string

import dynamic
import track


Material = collections.namedtuple('Material', 'straight turns ups, downs pillars')


def can_be_simplified(t, set_of_tracks):
    return any(st in set_of_tracks for st in t.simplify())


def compute_tracks(material):
    paths = dynamic.find_all_paths(material)
    print('number of paths:', len(paths))
    paths = set(map(track.normalize_path, paths))
    print('number of unique paths:', len(paths))
    tracks = [track.Track(p) for p in paths]
    tracks = [t for t in tracks if t.is_valid(material)]
    set_of_tracks = set(tracks)
    tracks = [t for t in tracks if not can_be_simplified(t, set_of_tracks)]
    print('number of unique paths:', len(tracks))
    return tracks


def main():
    parser = argparse.ArgumentParser(description='find all closed paths')
    parser.add_argument(
        '--turns',
        dest='turns', type=int, default=12, help='number of turn segments')
    parser.add_argument(
        '--straight',
        dest='straight', type=int, default=4,
        help='number of straight segments')
    parser.add_argument(
        '--ups',
        dest='ups', type=int, default=2, help='number of uphill segments')
    parser.add_argument(
        '--downs',
        dest='downs', type=int, default=2, help='number of downhill segments')
    parser.add_argument(
        '--pillars',
        dest='pillars', type=int, default=4, help='number of pillars')
    args = parser.parse_args()
    material = Material(
        turns=args.turns,
        straight=args.straight,
        ups=args.ups,
        downs=args.downs,
        pillars=args.pillars)

    tracks = compute_tracks(material)
    os.makedirs('report', exist_ok=True)
    with open('report/index.html', 'w') as report:
        report.write('<!doctype html>\n')
        report.write('<body>\n')
        report.write('<table>\n')
        report.write('<tr><th>descr<th>image</tr>\n')
        for i, t in enumerate(tracks[:100], start=1):
            report.write('<tr><td>%s</td>' % t.path)
            report.write('<td><img src="preview%02d.png"></td></tr>\n' % i)
            t.draw('report/preview%02d.png' % i)
        report.write('</table></body>\n')


if __name__ == '__main__':
    main()
