# bridges
# there has to be the same number of uphills as downhills
# length of up hills is limited every up hill after up hill needs
# 2 support pillars same for downhill

# for elevated track every piece needs 1 pillar ending piece needs two.
# that brings number of elevated tracks to maximaly 1x3 or 2x1

import argparse
import collections
import itertools
import math
import pickle
import string
import time


def shifts(track):
    for i in range(len(track)):
        yield track[i:] + track[:i] 


ROTATE_TRANSFORM = str.maketrans('RL', 'LR')
def normalize_track(track):
    # possible symmetries
    # translational - generate all translations and choose the biggest
    #                 lexicographycally
    # rotational    - change left rotation to right and choose the biggest
    #                 lexicographically
    # reverse path  - change the direction
    mirror_track = track.translate(ROTATE_TRANSFORM)
    reversed_track = track[::-1]
    reversed_mirror_track = mirror_track[::-1]
    return min(itertools.chain(
        shifts(track),
        shifts(mirror_track),
        shifts(reversed_track),
        shifts(reversed_mirror_track)
    ))


Pos = collections.namedtuple('Pos', 'ax bx ay by')
# Because sqrt(2) is irational number we have to track numbers in following base.
# ax, ay is position in the grid in multiples of sqrt(2)/2 ~ 0.71
# bx, by is position in the grid in multiples of 1-sqrt(2)/2 ~ 0.29

Material = collections.namedtuple('Material', 'straight turns ups, downs pillars')

State = collections.namedtuple('State', 'pos angle level material')
# material - is the number of remainin pieces

def add_pos(p1, p2):
    aax, abx, aay, aby = p1
    bax, bbx, bay, bby = p2
    return Pos(aax + bax, abx + bbx, aay + bay, aby + bby)

def material_pieces(m):
    return m.straight + m.turns + m.ups + m.downs

STR_SHIFT = (
    (1, 1, 0, 0),
    (1, 0, -1, 0),
    (0, 0, -1, -1),
    (-1, 0, -1, 0),
    (-1, -1, 0, 0),
    (-1, 0, 1, 0),
    (0, 0, 1, 1),
    (1, 0, 1, 0),
)

R_SHIFT = (
    (1, 0, 0, -1),
    (0, 1, -1, 0),
    (0, -1, -1, 0),
    (-1, 0, 0, -1),
    (-1, 0, 0, 1),
    (0, -1, 1, 0),
    (0, 1, 1, 0),
    (1, 0, 0, 1),
)

def dynamic_programming(material):
    border = set()
    border.add(State(pos=Pos(0, 0, 0, 0), angle=0, level=0, material=material))
    visited = set()
    for _ in range(material_pieces(material)):
        new_border = set()
        for s in border:
            m = s.material
            turns, angle, level = m.turns, s.angle, s.level
            if turns < angle and turns < 7 - angle:
                # It's not possible to turn back
                # with the current number of turns.
                continue
            dist_from_origin = max(map(abs, s.pos))
            if dist_from_origin > material_pieces(m):
                # It's not possible to return back
                # with the current number of segments.
                continue
            if m.pillars < level or (m.downs < level):
                continue
            if m.straight > 0:
                # Straight segment
                # We suppose one pillar per segment and level.
                npos = add_pos(s.pos, STR_SHIFT[angle])
                nstate = State(npos, angle, level, m._replace(straight=m.straight-1, pillars=m.pillars-level))
                new_border.add(nstate)
            if m.ups > 0:
                # Up slope
                # We suppose two pillars per segment and level.
                npos = add_pos(s.pos, STR_SHIFT[angle])
                nstate = State(npos, angle, level+1, m._replace(ups=m.ups-1, pillars=m.pillars - 2*level))
                new_border.add(nstate)
            if m.downs > 0 and level > 0:
                # Down slope
                # We suppose two pillars per segment and final level.
                # If the previous segment wasn't up slope we should
                # add level-times pillars. We don't know that prev. segment
                # in this alg. so we relax this condition.
                npos = add_pos(s.pos, STR_SHIFT[angle])
                nstate = State(npos, angle, level-1, m._replace(downs=m.downs-1, pillars=m.pillars - (level-1)))
                new_border.add(nstate)
            if m.turns > 0:
                # Turn left, right
                # We suppose one pillar per segment and level.
                npillars = m.pillars - level
                npos = add_pos(s.pos, R_SHIFT[angle])
                nstate = State(npos, (angle+1) % 8, level, m._replace(turns=turns-1, pillars=npillars))
                new_border.add(nstate)
                npos = add_pos(s.pos, R_SHIFT[(angle - 1) % 8])
                nstate = State(npos, (angle-1) % 8, level, m._replace(turns=turns-1, pillars=npillars))
                new_border.add(nstate)
        visited.update(new_border)
        border = new_border
    return visited


def get_neighbours(s):
    m = s.material
    angle, level = s.angle, s.level

    npos = add_pos(s.pos, STR_SHIFT[(angle - 4) % 8])
    straight = State(npos, angle, level, m._replace(straight=m.straight+1, pillars=m.pillars+level))
    up       = State(npos, angle, level-1, m._replace(ups=m.ups+1, pillars=m.pillars+2*(level-1)))
    down     = State(npos, angle, level+1, m._replace(downs=m.downs+1, pillars=m.pillars+level))

    npos = add_pos(s.pos, R_SHIFT[(angle - 5) % 8])
    right = State(npos, (angle-1) % 8, level, m._replace(turns=m.turns+1, pillars=m.pillars+level))

    npos = add_pos(s.pos, R_SHIFT[(angle - 4) % 8])
    left = State(npos, (angle+1) % 8, level, m._replace(turns=m.turns+1, pillars=m.pillars+level))

    return [('S', straight), ('U', up), ('D', down), ('R', right), ('L', left)]
    
    
def back_propagation(visited, material):
    end_pos = Pos(0, 0, 0, 0)
    end_state = State(end_pos, 0, 0, material)
    paths = []
    final = []
    for s in visited:
        if s.pos == end_pos and s.angle == s.level == 0 and s.material != material:
            paths.append(('', s))
    while paths:
        new_paths = []
        for path, s in paths:
            for segment, ps in get_neighbours(s):
                if ps == end_state:
                    final.append(segment + path)
                elif ps in visited:
                    new_paths.append((segment + path, ps))
        paths = new_paths
    return final


def compute_all_paths(material):
    t = time.clock()
    visited = dynamic_programming(material)
    print('frw took {:.2f}s'.format(time.clock() - t))
    t = time.clock()
    paths = back_propagation(visited, material)
    print('back took {:.2f}s'.format(time.clock() - t))
    print('number of paths:', len(paths))
    paths = set(map(normalize_track, paths))
    print('number of unique paths:', len(paths))
    return paths


def test_conflict(s1, l1, start1, end1, s2, l2, start2, end2):
    return False


def get_height(path):
    # Reconstruct height
    level = []
    cl = 0
    
    for s in path:
        level.append(cl)
        if s == 'U':
            cl += 1
        elif s == 'D':
            cl -= 1
    else:
        level.insert(0, cl)
    # minimal level should be 0
    ml = min(level)
    level = [cl - ml for cl in level]
    return level


STRAIGHT_SIZE = 1.0
TURN_SIZE = 2.0 * math.sin(math.pi / 8.0)


def get_pos(path):
    x = y = .0
    angle = 0
    pos = []
    for s in path:
        if s == 'R':
            angle += 1
            r = TURN_SIZE
        elif s == 'L':
            angle -= 1
            r = TURN_SIZE
        else:
            r = STRAIGHT_SIZE
        pos.append((x, y))
        a = angle * math.pi / 4.0
        x += math.cos(a) * r
        y += -math.sin(a) * r
    pos.append((x, y))
    return pos, angle


def validate_path(path, material):
    """Ensure that the paths do not intersect
    Also enforce more stricter condition on pillars.
    """
    if not path:
        return False
    if path.count('U') != path.count('D'):
        # unbalanced
        return False

    level = get_height(path)
    pos, angle = get_pos(path)

    if angle % 8 != 0:
        # does not return to original direction
        return False

    endx, endy = pos[-1]
    if math.fabs(endx) > 1e-10 or math.fabs(endy) > 1.e-10:
        # does not return to original point
        return False

    # count pillars and remove paths with lot of pillars
    lp = len(path)
    pillars = 0
    # up after a segment
    #   2 times level
    #   1 times level if the following segment is not down and there is no
    #   pass below (that's quite a hack so we do not consider that)
    # up after a down
    #   2 times level
    #   1 times level if the following segment is not down (same hack)
    # down after a segment
    #   2 times level - 1
    # down after an up (that's less than estimated)
    #   level - 1

    for i in range(lp):
        if path[i] == 'U':
            pillars += 2 * level[i]
        elif path[i] == 'D':
            pillars += level[i] - 1
            if path[(i-1) % lp] != 'U':
                # we can move one of support pillar backward
                # to support both segments
                pillars += level[i] - 1
        else:
            pillars += level[i]
    if material.pillars < pillars:
        return False

    for i in range(lp):
        for j in range(i):
            if test_conflict(
                path[i], level[i], pos[i], pos[(i+1) % lp],
                path[j], level[j], pos[j], pos[j+1],
            ):
                return False
    return True


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

    filename = 'paths.pickle'
    try:
        paths = pickle.load(open(filename, 'rb'))
    except IOError:
        paths =compute_all_paths(material)
        pickle.dump(paths, open(filename, 'wb'))
    paths = [p for p in paths if validate_path(p, material)]
    print('number of unique paths:', len(paths))


if __name__ == '__main__':
    main()