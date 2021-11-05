from flask import Flask, render_template, request, session, g, redirect, url_for, flash, Markup
from authlib.integrations.flask_client import OAuth
from urllib.request import Request, urlopen, URLError
import sqlite3 as sql
import argparse, re
from collections import defaultdict, namedtuple
import os
from functools import wraps
from collections import deque
import json

""" GLOBAL VARIABLES """
app = Flask(__name__)
TAG_SEPARATOR = '|'
NUM_TALKS = 50
DATABASE_SCHEMA_FILE = 'schema.sql'
DATABASE = 'annotations.db'
TABLE_NAME = 'annotations'
translation_type_dict = {0: 'target1', 1: 'target2', 2: 'mismatch', 3: 'mismatch'}
# REGEXs FOR EXTRACTING TERMS FROM ANNOTATIONS
term_regex = re.compile(r'<mark>(.*)</mark>')
highlight_pattern = re.compile(r'<span.*"true">(.*)</span>')
h_regex = re.compile(r'<h>(.*)</h>')

# FOR MESSAGE FLASHING
app.secret_key = ''
# FOR STORING STATE OF THE APPLICATION
user_data = dict()
user_talkid = dict()  # save current talk_id
user_turnid = dict()

""" OAUTH CODE """
# app.config['GOOGLE_CLIENT_ID'] = ''
# app.config['GOOGLE_CLIENT_SECRET'] = ''

CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth = OAuth(app)
oauth.register(
    name='google',
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @wraps(view)
    def wrapped_view(**kwargs):
        g.user = session.get('annotator_id')
        if isinstance(g.user, dict):
            g.user = g.user['email']
        if g.user is None:
            return redirect(url_for('login'))
        else:
            print(g.user)
        return view(**kwargs)
    return wrapped_view


@app.route('/login')
def login():
    #return google.authorize(callback=url_for('authorized', _external=True))
    redirect_uri = url_for('auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    # TODO: can delete user_data for current user (g.user) here
    session.pop('annotator_id', None)
    return redirect(url_for('login'))
    

@app.route('/login/authorized')
def auth():
    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token)
    session['annotator_id'] = user['email']
    return redirect(url_for('home'))


""" DATABASE CODE  """
# for representing rows from database
Row = namedtuple('Row', 'username, talk_id, term_id, real_id, link, german_ctx, english_ctx, gloss_ctx, german, english, gloss, en_ctx_h, gl_ctx_h, en_h, gl_h, confidence, is_annotated')


# for generating Row namedtuples from database rows
def namedtuple_factory(cursor, row):
    if row:
        return Row(*row)


def init_db():
    """ Load database schema file """
    with app.app_context():
        db = get_db()
        with app.open_resource(DATABASE_SCHEMA_FILE, mode='r') as f:
            cur = db.execute('SELECT name FROM sqlite_master WHERE type = "table"')
            tables = cur.fetchall()
            cur.close()
            if (TABLE_NAME,) not in tables:
                db.cursor().executescript(f.read())
        db.commit()


def insert_db(query, args=()):
    con = get_db()
    cur = con.cursor()
    cur.execute(query, args)
    con.commit()


def query_db(query, args=(), one=False, return_namedtuple=True):
    con = get_db()
    if return_namedtuple:
        con.row_factory = namedtuple_factory
    cur = con.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sql.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def fill_annotated_rows_from_db(from_db_path):
    """
    Fill the rows of the current, new database with annotated rows from a different database.
    Useful for transferring data from one SQLITE database to the other.
    :param from_db_path: Path to the database to transfer from.
    :return: None
    """
    with app.app_context():
        from_db = sql.connect(from_db_path)
        from_db.row_factory = namedtuple_factory
        query = 'SELECT * FROM annotations WHERE is_annotated=1;'
        cur = from_db.execute(query)
        rows = cur.fetchall()
        cur.close()

        for row in rows:
            insert_db('UPDATE annotations '
                      'SET username=?, talk_id=?, term_id=?, real_id=?, link=?, german_ctx=?, english_ctx=?, gloss_ctx=?, german=?, english=?, gloss=?, en_ctx_h=?, gl_ctx_h=?, en_h=?, gl_h=?, confidence=?, is_annotated=? '
                      'WHERE username=? AND talk_id=? AND term_id=?;',
                      ('anon', row.talk_id, row.term_id, row.real_id, row.link, row.german_ctx, row.english_ctx, row.gloss_ctx, row.german, row.english, row.gloss, row.en_ctx_h, row.gl_ctx_h, row.en_h, row.gl_h, row.confidence, row.is_annotated,
                       'None', row.talk_id, row.term_id)
                      )


""" ANNOTATION-SPECIFIC CODE """
UnannotatedSentence = namedtuple('UnannotatedSentence', ['talk_id', 'term_id', 'real_id', 'link', 'german_ctx', 'english_ctx', 'gloss_ctx', 'german', 'english', 'gloss'])


def load_agg_keywords():
    """
    Read in and store the aggregate keywords csv file
    :returns: A dictionary mapping source terms (aka keywords) to sets of their target language definitions
    and a set of the source terms in this dictionary
    """
    srckw2tgt = defaultdict(lambda: defaultdict(set))
    src_terms_in_dict = set()
    with open(args.csv, encoding='utf-8') as csv:
        for line in csv:
            split_line = line.strip().split(',')
            src_terms_in_dict.add(split_line[0])
            # skip dictionary definition in CSV; spkr_ids correspond to 1:trans, 2:brank, 3:arank, 4:srank
            for spkr_id, words in enumerate(split_line[2:], start=1):
                for word in words.split():
                    srckw2tgt[split_line[0]][spkr_id].add(word)
    return srckw2tgt, src_terms_in_dict


def load_sentences_from_dirs(src_bio_dir, trans_dir, b_dir, a_dir, s_dir):
    # load data from each corresponding directory
    dirs = [src_bio_dir, trans_dir, b_dir, a_dir, s_dir]
    all_sents = [[], [], [], [], []]  # [[src1lines, src2lines,...], [trans1lines, trans2lines, ...], ...]
    for d_i, dir in enumerate(dirs):
        dir = os.path.abspath(dir)
        for file in sorted(os.listdir(dir)):
            if file.endswith('.txt'):
                with open(os.path.join(dir, file), encoding='utf-8') as f:
                    all_sents[d_i].append(f.readlines())
    return all_sents

def load_sentences_from_files(cur_src, cur_tgt, prev_src, prev_tgt):
    files = [cur_src, cur_tgt, prev_src, prev_tgt]
    all_sents = []  # [[src1lines, src2lines,...], [trans1lines, trans2lines, ...], ...]
    for f_i, filepath in enumerate(files):
        with open(filepath, encoding='utf-8') as f:
            all_sents.append(f.readlines())
    return all_sents

def read_data(data):
    """
    Load a list of parallel sentences with source terms labeled with BIO tags from files.
    :param src_bio_dir: Directory with source sentences, each word has a BIO tag
    :param trans_dir: Directory with translator's sentences
    :param b_dir: Directory with Brank interpreter's sentences
    :param a_dir: Directory with Arank interpreter's sentences
    :param s_dir: Directory with Srank interpreter's sentences
    :return: A list of UnannotatedSentence namedtuples, each contains a `row' of information to put in the database.
    """
    sents_to_annotate = []
    for talk_id in range(NUM_TALKS):
        data_path = f"{data}{str(talk_id+1)}.json"
        with open(data_path, 'r') as file:
            all_sents = json.load(file)
        for term_id, sample in all_sents.items():
            sents_to_annotate.append(UnannotatedSentence(talk_id, term_id, sample['video_id'], sample['video_link'], \
                                    "<br><br>".join(sample['german_ctx']), "<br><br>".join(sample['english_ctx']), "<br><br>".join(sample['gloss_ctx']), \
                                    sample['german'], sample['english'], sample['gloss']))
    return sents_to_annotate

def fill_db(sents_to_annotate):
    """
    Init a database with (username, talk_id, term_id) primary key
    :param sents_to_annotate: A list of tuples of
    :return: None
    """
    annotated_translation_type = None
    is_annotated = 0
    username = 'None'
    with app.app_context():
            for (talk_id, term_id, real_id, link, german_ctx, english_ctx, gloss_ctx, german, english, gloss) in sents_to_annotate:
                insert_db(
                    """INSERT INTO annotations (username, talk_id, term_id, real_id, link, german_ctx, english_ctx, gloss_ctx, german, english, gloss, en_ctx_h, gl_ctx_h, en_h, gl_h, confidence, is_annotated
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);""",
                    (username, talk_id, term_id, real_id, link, german_ctx, english_ctx, gloss_ctx, german, english, gloss, None, None, None, None, None, is_annotated)
                )

def get_num_annotated():
    return query_db(
            'SELECT COUNT(*) '
            'FROM annotations '
            'WHERE talk_id=? AND username=? AND is_annotated=1;',
            (user_talkid[g.user], g.user, ), return_namedtuple=False)[0][0]

@app.route('/')
@login_required
def home():
    """
    Render the homepage of the application.
    :return: The rendered html template
    """
    print("USER ", g.user)
    if g.user not in user_data:
        user_data[g.user] = load_users_data(g.user)
    num_completed = dict()
    num_total = dict()
    for i in range(NUM_TALKS):
        num_completed['completed' + str(i)] = query_db(
            'SELECT COUNT(*) '
            'FROM annotations '
            'WHERE talk_id=? AND username=? AND is_annotated=1;',
            (i,g.user,), return_namedtuple=False)[0][0]
        num_total['total' + str(i)] = query_db(
            'SELECT COUNT(*) '
            'FROM annotations '
            'WHERE talk_id=? AND username="None"',
            (i,), return_namedtuple=False)[0][0]
    num_completed['completed'] = sum(num_completed.values())
    num_total['total'] = sum(num_total.values())
    return render_template('home.html', **num_completed, **num_total)

@app.route('/tasks/<int:talk_id>/menu')
@login_required
def menu(talk_id):
    tbl_data = query_db('SELECT * FROM annotations WHERE talk_id=? AND username=? AND is_annotated=1 ORDER BY term_id;', (talk_id, g.user, ))
    menu_rows = []
    answers = []
    confidence = []
    for i, row in enumerate(tbl_data):
        answer = []
        menu_rows.append(row.gloss) 
        confidence.append(row.confidence)
        for res in [row.en_ctx_h, row.gl_ctx_h, row.en_h, row.gl_h]:
            match = h_regex.search(res)
            while match:
                answer.append(res[match.start()+3:match.end()-4])
                res = res[match.end() + 1:]
                match = h_regex.search(res)
        if len(answer) == 0:
            answers.append("NO ANSWER")
        else:
            answers.append(answer)
    return render_template('menu.html', talk_id=talk_id, num_rows = len(menu_rows), menu_rows=menu_rows, answers=answers, confidence=confidence)

@app.route('/tasks/<int:talk_id>/<int:turn_id>', methods=["GET"])
@login_required
def turn(talk_id, turn_id):
    """
    Load the task template page with a parallel sentence for annotation.
    Users highlight a term in the target language sentence.
    :param talk_id: An integer index of the talk we are pulling sentences from.
    :return: The rendered html template
    """
    cur_turn = get_num_annotated()
    num_total = query_db(
            'SELECT COUNT(*) '
            'FROM annotations '
            'WHERE talk_id=?',
            (talk_id,), return_namedtuple=False)[0][0]
    if turn_id > cur_turn:
        print('Skipped tasks')
        flash('You have not yet annotated example {}. Please annotate example {}.'.format(cur_turn+1, cur_turn+1))
        return redirect(url_for('turn', talk_id=talk_id, turn_id=cur_turn))
    global user_data
    user_talkid[g.user] = talk_id
    if g.user not in user_turnid:
        user_turnid[g.user] = dict()
    user_turnid[g.user][talk_id] = turn_id

    try:
        next_row = user_data[g.user][talk_id][turn_id]
        return render_template('task.html',
                            german_ctx=next_row.german_ctx,
                            english_ctx=next_row.english_ctx,
                            gloss_ctx=next_row.gloss_ctx,
                            german=next_row.german,
                            english=next_row.english,
                            gloss=next_row.gloss,
                            id_task=talk_id+1,
                            id_turn=turn_id + 1,
                            real_id=next_row.real_id,
                            link=next_row.link,
                            talk_id=next_row.talk_id,
                            num_remaining=num_total - cur_turn
                            )
    except:
        return home()

@app.route('/tasks/<int:talk_id>', methods=["GET"])
@login_required
def task(talk_id):
    """
    Load the task template page with a parallel sentence for annotation.
    Users highlight a term in the target language sentence.
    :param talk_id: An integer index of the talk we are pulling sentences from.
    :return: The rendered html template
    """
    global user_data
    user_talkid[g.user] = talk_id
    cur_turn = get_num_annotated()
    num_total = query_db(
            'SELECT COUNT(*) '
            'FROM annotations '
            'WHERE talk_id=? AND username="None"',
            (talk_id,), return_namedtuple=False)[0][0]
    print("talk_id", talk_id)
    print("cur_turn", cur_turn)
    print("num_total", num_total)
    if cur_turn == num_total:
        print('No data left in file. Redirecting to home...')
        flash('No data left to annotate for Talk {}. Please select a different talk.'.format(talk_id+1))
        print("home", url_for('home'))
        return redirect(url_for('home'))
        #return home()
    
    return redirect(url_for('turn', talk_id=talk_id, turn_id=cur_turn))


def get_highlight_span(sen):
    highlight_pattern = re.compile(r'<span.*"true">(.*)</span>')
    head_pattern = '"true">'
    tail_pattern = '</span>'
    match = highlight_pattern.search(sen)
    matches = []
    offset = 0
    while match:
        head_start = sen.find(head_pattern)
        tail_start = sen.find(tail_pattern)
        a = match.start()
        b = a + tail_start - head_start - len(head_pattern)
        matches.append([a + offset,b + offset])
        offset = tail_start+1 - (head_start + len(head_pattern) - match.start()) - len(tail_pattern)
        sen = sen[tail_start+1:]
        match = highlight_pattern.search(sen)
    return matches

def tag_highlight_words(sen):
    sen_out = re.sub(r'<span.*?"true">', '<h>', sen)
    sen_out = sen_out.replace('</span>', '</h>')
    if "<h>" in sen_out:
        return sen_out
    else:
        return ""

@app.route('/add_row', methods=["POST"])
@login_required
def add_row():
    """
    Update the SQLITE database with the annotated parallel sentence which we retrieve from a request form.
    :return: The rendered html template
    """
    global user_data
    row = user_data[g.user][user_talkid[g.user]][user_turnid[g.user][user_talkid[g.user]]]
    outd = request.form.to_dict()
    button_id = outd['button_id']
    en_ctx_h = tag_highlight_words(outd['english_ctx'])
    gl_ctx_h = tag_highlight_words(outd['gloss_ctx']) 
    en_h = tag_highlight_words(outd['english']) 
    gl_h = tag_highlight_words(outd['gloss']) 
    confidence = button_id if button_id != '4' else None
    username = g.user
    insert_db(
                    """INSERT INTO annotations (username, talk_id, term_id, real_id, link, german_ctx, english_ctx, gloss_ctx, german, english, gloss, en_ctx_h, gl_ctx_h, en_h, gl_h, confidence, is_annotated
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(username, talk_id, term_id) DO UPDATE SET german_ctx=?, english_ctx=?, gloss_ctx=?, german=?, english=?, gloss=?, en_ctx_h=?, gl_ctx_h=?, en_h=?, gl_h=?, confidence=?;""",
                    (g.user, row.talk_id, row.term_id, row.real_id, row.link, row.german_ctx, row.english_ctx, row.gloss_ctx, row.german, row.english, row.gloss, en_ctx_h, gl_ctx_h, en_h, gl_h, confidence, 1,
                      row.german_ctx, row.english_ctx, row.gloss_ctx, row.german, row.english, row.gloss, en_ctx_h, gl_ctx_h, en_h, gl_h, confidence)
                )
    return redirect(url_for('task', talk_id=user_talkid[g.user]))


@app.route('/status', methods=["GET"])
@login_required
def status():
    """
    Use this hidden webpage for checking the status of the annotation process
    :return: The rendered html template.
    """
    usernames = [tup[0] for tup in query_db('SELECT DISTINCT username FROM annotations WHERE username != ?;', ('None',),
                                            return_namedtuple=False)]
    num_annotated = []
    for username in usernames:
        num_annotated.append(query_db('SELECT COUNT(*) FROM annotations WHERE username=?;', (username,),
                             return_namedtuple=False)[0][0])
    total_num_annotated = sum(num_annotated)
    total_annotations_required = query_db('SELECT COUNT(*) FROM annotations;', return_namedtuple=False)[0][0]
    return render_template('status.html', usernames_and_num_annotated=list(zip(usernames, num_annotated)),
                           total_num_annotated=total_num_annotated,
                           total_annotations_required=total_annotations_required)


def load_users_data(username):
    """
    Return a user's data to be stored in their entry in the user_data dictionary
    :param username: A username string.
    :return: A list of deques of size NUM_TALKS. Each element in the deque is a Row namedtuple obtained from the
    SQLITE database.
    """
    print('Loading user data into memory for username:', username)
    with app.app_context():
        tbl_data = query_db('SELECT * FROM annotations WHERE username="None" ORDER BY term_id;')
    # load into list of deques, one per talk (number of separate categories) to annotate
    return [deque([row for row in tbl_data if row.talk_id == i]) for i in range(NUM_TALKS)]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Annotation interface.')
    parser.add_argument('-data', type=str, help='Path to the json data file')
    parser.add_argument('--init-db', action='store_true',
                        help='Initialize the database. This should be called the first time the program is run so that '
                             'the SQLITE database can be setup and loaded with data.')
    parser.add_argument('--from-db', type=str, help='Path to a database file to initialize this one from.')
    parser.add_argument('--server', action='store_true', help='Run on server.')
    parser.add_argument('--port', type=int, default=5000, help='Port on which to run the server (default 5000)')
    args = parser.parse_args()

    if args.init_db:
        init_db()
        sents_to_annotate = read_data(args.data)
        fill_db(sents_to_annotate)
        if args.from_db:
            fill_annotated_rows_from_db(args.from_db)
        exit(0)

    if args.server:
        app.run('0.0.0.0', port=args.port, threaded=True)
    else:
        app.run(port=args.port)  # run app locally
