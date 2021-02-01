
void tis_signal_handler(int sig) {
  return;
}

void (*signal(int sig, void (*func)(int)))(int) {
  return &tis_signal_handler;
}

#include <sys/time.h>

#define __CURRENT_TIME 1466335969L

/* The libc 'time' function stub. */
time_t time(time_t *timer) {
  return __CURRENT_TIME;
}

struct tm *localtime(const time_t *timer) {
  return NULL;
}

int gettimeofday(struct timeval *tv, struct timezone *tz) {
  tv->tv_sec = __CURRENT_TIME;
  tv->tv_usec = 455745;
  return 0;
}
