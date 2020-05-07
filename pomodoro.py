import sys
import time
from datetime import datetime, timedelta
import threading
import sqlite3
from plyer import notification
# import send_message

DEFAULT_PERIOD = 25
DEFAULT_SHORT_REST = 5
DEFAULT_LONG_REST = 5
UPDATE_DURATION_SEC = 1

elapsed_min = 0
exit_thread = False


class Database:
    def __init__(self):
        self.conn = sqlite3.connect('pomodoro.db')
        self.cur = self.conn.cursor()

        self.table_name = 'pomodoro_log'
        self.columns = ['task', 'start', 'finish', 'duration_min']

        # テーブルの存在確認
        try:
            self.cur.execute("select * from {}".format(self.table_name))
            # カラムの確認
            if len(self.columns) != len(self.cur.description):
                raise Exception('keys and description are mismatch.')

            for k, d in zip(self.columns, self.cur.description):
                if k != d[0]:
                    raise Exception(
                        f'keys and description are mismatch.\n{k} != {d[0]}')

        except sqlite3.Error:  # as e:
            # 無ければ作る
            s = 'create table {}({})'.format(
                self.table_name, ','.join(self.columns))
            print(s)
            self.cur.execute(s)

    def __del__(self):
        self.conn.close()

    def add_date(self, task, start, finish, duration_min):
        s = 'insert into {} ({}) values ({})'.format(
            self.table_name,
            ','.join(self.columns),
            ','.join(['?'] * len(self.columns))
        )
        c = self.cur.executemany(s, [(task, start, finish, duration_min)])
        self.conn.commit()


def minutes(td: timedelta):
    return td.total_seconds() // 60


def get_h_m_s(td: timedelta):
    m, s = divmod(td.total_seconds(), 60)
    h, m = divmod(m, 60)
    return h, m, s


def delta2str(td: timedelta):
    hms = get_h_m_s(td)
    hms = [int(x) for x in hms]
    return f'{hms[0]:02d}:{hms[1]:02d}:{hms[2]:02d}'


def parse_period():
    success = False
    while not success:
        period_str = input('period [min] (default: 25min.): ')
        if period_str == '':
            period_min = DEFAULT_PERIOD
            success = True
        else:
            try:
                period_min = int(period_str)
                success = True
            except Exception as e:
                print(e)
                success = False

    return period_min


def timer_thread(period_min):
    global exit_thread, elapsed_min
    start_time = datetime.now()

    exit_thread = False
    elapsed_min = 0
    while (elapsed_min < period_min) and (not exit_thread):
        elapsed = datetime.now() - start_time
        elapsed_min = minutes(elapsed)

        sys.stdout.write(f'{delta2str(elapsed)} / {period_min:02d}\r')
        sys.stdout.flush()
        time.sleep(UPDATE_DURATION_SEC)

    sys.stdout.write('\n')
    sys.stdout.flush()


def run_timer(task_name, period_min):
    global exit_thread, elapsed_min

    start_time = datetime.now()
    mes = f'"{task_name}" start {start_time}'
    notify(mes, False)

    ttimer = threading.Thread(
        target=timer_thread, kwargs={'period_min': period_min})
    ttimer.start()

    # joinで待つと、KeyboardInterruptが補足できない
    try:
        while ttimer.is_alive():
            time.sleep(UPDATE_DURATION_SEC)

    except KeyboardInterrupt:
        exit_thread = True
        while ttimer.is_alive():
            time.sleep(UPDATE_DURATION_SEC)

    ttimer.join()

    finish_time = datetime.now()

    mes = f'"{task_name}" finish {finish_time} elapsed: {elapsed_min}'
    notify(mes, True)

    return task_name, start_time, finish_time, elapsed_min


def one_pomodoro():
    task_name = input('task: ')
    period_min = parse_period()

    return run_timer(task_name, period_min)


def short_rest():
    task_name = 'short rest'
    period_min = DEFAULT_SHORT_REST

    return run_timer(task_name, period_min)


def long_rest():
    task_name = 'long rest'
    period_min = DEFAULT_LONG_REST

    return run_timer(task_name, period_min)


def run_and_add_db(f):
    task_name, start_time, finish_time, elapsed_min = f()
    d.add_date(task_name, start_time, finish_time, elapsed_min)


def one_pomodoro_and_add_db():
    run_and_add_db(one_pomodoro)


def short_rest_and_add_db():
    run_and_add_db(short_rest)


def long_rest_and_add_db():
    run_and_add_db(long_rest)


def notify(mes, notify_center):
    print(mes)
    if notify_center:
        notification.notify(
            title="Finish period",
            message=mes,
            app_name="pomodoro timer"
        )

    # global token, uid, sa_id
    # if sa_id:
    #     rd = send_message.sendMessage(token, uid, sa_id, mes)
    #     print(rd)


if __name__ == "__main__":
    d = Database()

    # init for rocket.chat notifincation
    # global token, uid, sa_id
    # channel = 'times_sano'
    # token, uid = send_message.login()

    # ch = send_message.listChannels(token, uid)
    # print(ch)
    # sa_id = send_message.getChannelOrGroupId(ch, channel)

    while True:
        one_pomodoro_and_add_db()
        try:
            r = input('take break [s/l]: ')
        except KeyboardInterrupt:
            break
        if r.lower() == 'l':
            long_rest_and_add_db()
        else:
            short_rest_and_add_db()

    # rd = send_message.logout(token, uid)
    # print(rd)
