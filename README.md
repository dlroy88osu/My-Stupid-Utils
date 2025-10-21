# My_Stupid_Utils

Just some random utils I use... Nothing crazy but feel free to 'em.


## Python:

- [Python Logger](./python/logger/logger.py)
  - Simple thread safe logger that runs using a queue to ensure order. Nothing to init, no fuss.
    ```python
    def test():
        title('This is a title')

        trace('This is a trace message')
        debug('This is a debug message')
        info('This is an info message')
        warn('This is a warn message')
        error('This is an error message')

        sep('😈', new_line_before=True, is_emoji=True)
        sep('~', 'yellow', new_line_before=True)

        # can directly pass exception - class to left of arrow msg to the right
        error('This is an error message', Exception('This is a test exception'))

        # kills program
        panic('This is a panic message', Exception('This is a test exception'))


    if __name__ == '__main__':
        test()
    ```
  - Console out
  - ![Output](./python/logger/logger_out.png)
