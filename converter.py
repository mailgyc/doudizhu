import collections


def main():
    junks = {}
    with open('demo', 'r', encoding='UTF-8') as fp:
        for line in fp:
            cols = line.split()
            if not cols:
                continue

            if cols[0].endswith(','):
                cols[0] = cols[0][0:-1]

            if not cols[-1].startswith('"'):
                cols[-1] = '"' + cols[-1]

            if cols[-1].startswith('"/'):
                cols[-1] = '"' + cols[-1][2:]

            if cols[0] in junks:
                junks[cols[0]].append(cols[-1])
            else:
                junks[cols[0]] = [cols[-1]]

    junks = collections.OrderedDict(sorted(junks.items()))
    for k, v in junks.items():
        print('junks.put({}, new String[]{{{}}});'.format(k, ', '.join(v)))

if __name__ == '__main__':
    main()
