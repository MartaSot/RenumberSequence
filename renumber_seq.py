import os
import sys
import shutil
import logging
from datetime import datetime
from optparse import OptionParser, OptionGroup

'''
Project: RenumberSequence

Module: renumber_seq.py

Summary: This tool renumber sequences of images. It takes as many paths to a directories as you need.
The tool renames the files in each directory so that each sequence remains in the same order,
but the files are renumbered sequentially.

Created: February 5th, 2022

Contact: Marta G. Sotodosos (martagsotodosos@gmail.com)
'''

DATE = datetime.now().strftime('%y-%m-%d_%H-%M-%S')
TEMP_SUFIX = '_tmp_' + DATE

logger = logging.getLogger('renaming sequence')


def get_script_last_mod_datetime():
    """Get the last time the script has been modified.

    Returns:
        string: date of the last modification.
    """
    last_mod = 'N/A'
    try:
        script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        script_name = os.path.basename(__file__)
        script_path = os.path.join(script_dir, script_name)
        last_modified_ts = os.path.getmtime(script_path)
        last_modified_datetime = datetime.fromtimestamp(last_modified_ts)
        last_mod = last_modified_datetime.strftime('%b%e %Y %I:%M:%S %p')

        if (last_mod[11] == '0'):
            last_mod = last_mod[:10] + ' ' + last_mod[12:]
    except Exception as e:
        pass
    return last_mod.upper()


def get_options():
    """Get the options and arguments the script has been called with.

    Returns:
        list, list: first list with the options and the second with the arguments.
    """

    # This function keeps a nice format in the help text.
    def pad(string): return string.ljust(80)

    description = ('This tool renumbers sequences of images. It takes as many paths to a ' +
                   'directories as you need to renumber as arguments. The tool renames ' +
                   'the files in each directory so that each sequence remains in the same ' +
                   'order, but the files are renumbered sequentially. You can define both' +
                   ' the start number in the sequence and the legth of this number, ' +
                   'the usused position will be filled with zeros. If you do not define ' +
                   'a path in the arguments, the script will over the current directory.')
    author = 'Marta G. Sotodosos (martagsotodosos@gmail.com)'
    usage = 'usage: %prog [options] $ARGS'

    parser = OptionParser(usage=usage, epilog=None)

    parser.add_option('-s', '--start', action='store', default=1, type=int,
                      help=(pad('Starting image number. By default, 1')))
    parser.add_option('-l', '--length', action='store', default=2, type=int,
                      help=(pad('Define the length of our image number. Zeros are used to fill ' +
                      'the unused digits. By default, length=2.')))

    # Display Description, Last Modified Time, Author.
    mtime = get_script_last_mod_datetime()
    group_last_modified = OptionGroup(parser, 'Last Modified', mtime)
    group_desc = OptionGroup(parser, 'Description', description)
    group_author = OptionGroup(parser, 'Author', author)

    parser.add_option_group(group_desc)
    parser.add_option_group(group_last_modified)
    parser.add_option_group(group_author)

    (options, args) = parser.parse_args()
    return (options, args)


def restore_original_names(renaming_dict):
    """Given the relation between the original and the current names,
       it restores the original file names. This restore is used when
       an exception is caught during the main renaming process, such as when
       a file without modification permissions is found.

    Args:
        renaming_dict (dict): Relation between original names and current names

    """
    for org_name, curr_name in renaming_dict.items():
        os.rename(curr_name, org_name)


def renumber_files(path, start, length):
    """Given a path it renames the sequence file inside.

    Args:
        start (int): new start frame of the renamed sequence.
        length (int): padding size used.

    """
    # Check if the path exists.
    if not os.path.exists(path):
        logger.warning('Path "%s" does not exist. Skipping path...'%path)
        return

    # Check if the path is a directory.
    if not os.path.isdir(path):
        logger.warning('Path "%s" is not a directory. Skipping path...'%path)
        return

    files = os.listdir(path)
    # Check if the directory is empty.
    if not files:
        logger.warning('Path "%s" is empty. Skipping path...'%path)
        return

    # renaming_dict: Dict to keep the relation between the original name and the current one
    # just in case the process fails and the original names need to be restored.
    # The dict is updated after every rename() and it will be used if any exception
    # is caught during the process.
    renaming_dict = {}

    seqs_data_dict = {}

    try:
        for file in files:
            full_path = '%s/%s'%(path, file)
              
            # If the subpath is not a file, it is skipped.
            if not os.path.isfile(full_path):
                continue

            data = file.split('.')

            # Skip those files that do not meet the name convention <name>.<number>.<ext>
            if len(data) != 3:
                continue

            name, number, ext = data[0], data[1], data[2]

            # Skip those files that do not meet the name convention. (<number> must be numeric)
            if not number.isnumeric():
                continue

            # Group the file by sequence. (name and ext)
            if (name, ext) not in seqs_data_dict.keys():
                seqs_data_dict[name, ext] = [number]
            else:
                seqs_data_dict[name, ext].append(number)

            # Rename the file as tmp to avoid duplicating existing names.
            tmp_path = '%s/%s.%s.%s'%(path, name, number + TEMP_SUFIX, ext)
            os.rename(full_path, tmp_path)

            # The dictionary renaming_dict is updated with the temporal name.
            renaming_dict[full_path] = tmp_path

        # Once the files are grouped by sequence, the files are ordered by number.
        for name, ext in seqs_data_dict.keys():
            img_list = seqs_data_dict[name, ext]
            img_list.sort(key=int)
            # Rename files in sequence starting in 01, remaining the original order.
            frame_number = start
            for number in img_list:
                full_path = '%s/%s.%s.%s'%(path, name, number + TEMP_SUFIX, ext)
                new_path = '%s/%s.%s.%s'%(path, name, str(frame_number).zfill(length), ext)
                os.rename(full_path, new_path)

                # The dictionary renaming_dict is updated with the new name.
                renaming_dict[full_path] = new_path

                frame_number += 1
    except Exception as e:
        logger.error('Error found renaming files on %s'%path)
        logger.error(str(e))
        logger.error('Skipping directory...')
        restore_original_names(renaming_dict)


def main():
    """Parse the arguments the script was executed with and rename the files
    in the given directories, with the options the user specified.

    """
    (options, args) = get_options()

    # If no directory is provided in the args, the script will be ran over the current location.
    if len(args) == 0:
        args.append(os.getcwd())

    # Run the script over each directory in args
    for path in args:
        renumber_files(path, options.start, options.length)


if __name__ == '__main__':
    main()
