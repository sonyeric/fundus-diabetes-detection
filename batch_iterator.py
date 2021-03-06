import numpy as np
from Queue import Queue
import threading
from time import time
import data_util
import pdb

class BatchIterator(object):

    def __init__(self, files, labels, batch_size, normalize=None, process_func=None, testing=None):
        self.files = np.array(files)
        self.labels = labels
        self.n = len(files)
        self.batch_size = batch_size
        self.testing = testing

        if normalize is not None:
            self.mean, self.std = normalize
            #self.mean = np.load(mean)
            #self.std = np.load(std)
        else:
            self.mean = 0
            self.std = 1

        if process_func is None:
            process_func = lambda x, y, z: x
        self.process_func = process_func

        if not self.testing:
            self.create_index = lambda: np.random.permutation(self.n)
        else:
            self.create_index = lambda: range(self.n)


        self.indices = self.create_index()
        assert self.n >= self.batch_size


    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def get_permuted_batch_idx(self):
        if len(self.indices) <= self.batch_size:
            new_idx = self.create_index()
            self.indices = np.hstack([self.indices, new_idx])

        batch_idx = self.indices[:self.batch_size]
        self.indices = self.indices[self.batch_size:]

        return batch_idx

    def next(self):
        batch_idx = self.get_permuted_batch_idx()
        batch_files = self.files[batch_idx]
        batch_X = data_util.load_images(batch_files)
        batch_X = self.process_func(batch_X, (self.mean, self.std), self.testing)
        batch_y = self.labels[batch_idx]
        return (batch_X, batch_y)

class PairedBatchIterator(BatchIterator):

    def __init__(self, files, labels, batch_size, normalize=None, process_func=None, testing=None):
        self.files = np.array(files)
        self.labels = np.array(labels).astype(np.int32)
        self.n = len(files)
        self.batch_size = batch_size // 2 # divide the batch_size by 2 to count how many pairs there are
        self.testing = testing

        if normalize is not None:
            self.mean, self.std = normalize
            #self.mean = np.load(mean)
            #self.std = np.load(std)
        else:
            self.mean = 0
            self.std = 1

        if process_func is None:
            process_func = lambda x, y, z: x
        self.process_func = process_func

        if not self.testing:
            self.create_index = lambda: np.random.permutation(self.n)
        else:
            self.create_index = lambda: range(self.n)


        self.indices = self.create_index()
        assert self.n >= self.batch_size


    def next(self):
        batch_idx = self.get_permuted_batch_idx()
        batch_files = self.files[batch_idx]
        batch_labels = self.labels[batch_idx]
        batch_files, batch_y = unpack(batch_files, batch_labels)
        batch_X = data_util.load_images(batch_files)
        batch_X = self.process_func(batch_X, (self.mean, self.std), self.testing)
        return (batch_X, batch_y)

def unpack(files, labels):
    """
    This function exploits the fact that the loaded files and labels are paired.
    To create a batch with these paired data, we take the left filess and labels to form the
    first half of the batch and take the right files and labels to form the latter half.
    """

    left = []
    right = []
    left_labels = []
    right_labels = []
    for image_pair, label_pair in zip(files, labels):
        left.append(image_pair[0])
        right.append(image_pair[1])
        left_labels.append(label_pair[0])
        right_labels.append(label_pair[1])
    left.extend(right)
    left_labels.extend(right_labels)
    return left, np.array(left_labels)

def threaded_iterator(iterator, num_cached=50):
    queue = Queue(maxsize=num_cached)
    sentinel = object()

    def producer():
        for item in iterator:
            queue.put(item)
        queue.put(sentinel)

    thread = threading.Thread(target=producer)
    thread.daemon = True
    thread.start()

    item = queue.get()
    while item is not sentinel:
        yield item
        queue.task_done()
        item = queue.get()




