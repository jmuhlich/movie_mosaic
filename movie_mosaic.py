import sys
import os
import shutil
import errno
import codecs
import re
import argparse
import collections
import jinja2


Cell = collections.namedtuple(
    'Cell',
    'row column rc_address image_filename movie_filename'
    )


def main(argv):

    argparser = argparse.ArgumentParser(
        description="Build an HTML gallery for an array of static images and "
        "associated movie clips.")
    argparser.add_argument('-c', '--columns',
                           help="Number of columns in the mosaic (can be "
                           "auto-detected from the data)")
    argparser.add_argument('-r', '--rows',
                           help="Number of rows in the mosaic (can be "
                           "auto-detected from the data)")
    argparser.add_argument('-o', '--output_path', default='./output',
                           help="Location for HTML output (default: "
                           "%(default)s)")
    argparser.add_argument('data_path',
                           help="Location of the images and movies")
    args = argparser.parse_args(argv)

    rc_address_pattern = r'r(\d+)c(\d+)'
    image_filename_pattern = re.compile(rc_address_pattern +
                                        r'.*\.(?:png|jpg|jpeg)$')
    movie_filename_pattern = re.compile(rc_address_pattern + r'.*\.mp4$')
    image_filenames = {}
    movie_filenames = {}
    errors = False
    for filename in os.listdir(args.data_path):
        image_match = image_filename_pattern.search(filename)
        movie_match = movie_filename_pattern.search(filename)
        if image_match:
            match = image_match
            filename_map = image_filenames
        elif movie_match:
            match = movie_match
            filename_map = movie_filenames
        else:
            continue
        rc_coords = tuple(map(int, match.groups()))
        if rc_coords in filename_map:
            rc_address = rc_formatter(*rc_coords)
            print >>sys.stderr, ("More than one image/movie file found for "
                                 "location {}:".format(rc_address))
            print >>sys.stderr, " ", filename_map[rc_coords], filename
            errors = True
        else:
            filename_map[rc_coords] = filename
    if errors:
        return 1

    cells = []
    mkdirp(args.output_path)
    for (row, column), image_filename in image_filenames.items():
        movie_filename = movie_filenames[(row, column)]
        rc_address = rc_formatter(row, column)
        cells.append(Cell(row, column, rc_address, image_filename, movie_filename))
        for filename in image_filename, movie_filename:
            src_path = os.path.join(args.data_path, filename)
            dest_path = os.path.join(args.output_path, filename)
            shutil.copyfile(src_path, dest_path)

    row_min = min(c.row for c in cells)
    row_max = max(c.row for c in cells)
    column_min = min(c.column for c in cells)
    column_max = max(c.column for c in cells)
    print 'rows: {}-{}'.format(row_min, row_max)
    print 'cols: {}-{}'.format(column_min, column_max)
    table = collections.defaultdict(dict)
    for cell in cells:
        table[cell.row][cell.column] = cell
    row_numbers = range(row_min, row_max + 1)
    column_numbers = range(column_min, column_max + 1)

    src_path = os.path.dirname(__file__)
    template_path = os.path.join(src_path, 'templates')
    template_loader = jinja2.FileSystemLoader(template_path)
    template_env = jinja2.Environment(loader=template_loader,
                                      undefined=jinja2.StrictUndefined)
    template = template_env.get_template('index.html')
    data_names = 'table cells row_numbers column_numbers'.split()
    # Take a "slice" of locals corresponding to the names in data_names.
    data = dict(zip(data_names, map(locals().get, data_names)))
    content = template.render(data)
    html_filename = os.path.join(args.output_path, 'index.html')
    with codecs.open(html_filename, 'w', 'utf-8') as out_file:
        out_file.write(content)

    static_output_path = os.path.join(args.output_path, 'static')
    shutil.rmtree(static_output_path, ignore_errors=True)
    shutil.copytree(os.path.join(src_path, 'static'), static_output_path)

    globals().update(locals()) # XXX


def rc_formatter(row, column):
    return 'r{}c{}'.format(int(row), int(column))


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST: raise

    
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
