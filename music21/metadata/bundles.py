# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Name:         bundles.py
# Purpose:      music21 classes for representing score and work meta-data
#
# Authors:      Christopher Ariza
#               Michael Scott Cuthbert
#               Josiah Oberholtzer
#
# Copyright:    Copyright © 2010, 2012-13 Michael Scott Cuthbert and the music21
#               Project
# License:      LGPL, see license.txt
#------------------------------------------------------------------------------


import os
import time
import unittest

from music21 import common
from music21 import exceptions21
from music21 import freezeThaw
from music21.ext import six

if six.PY3:
    unicode = str # @ReservedAssignment


#------------------------------------------------------------------------------


from music21 import environment
environLocal = environment.Environment(os.path.basename(__file__))


#------------------------------------------------------------------------------


class MetadataEntry(object):
    '''
    An entry in a metadata bundle.

    The metadata entry holds information about the source of the metadata,
    and can be parsed to reconstitute the score object the metadata was
    derived from:

    ::

        >>> from music21 import metadata
        >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
        >>> metadataEntry = coreBundle.search('bwv66.6')[0]
        >>> metadataEntry
        <music21.metadata.bundles.MetadataEntry: bach_bwv66_6_mxl>

    The source path of the metadata entry refers to the file path at which its
    score file is found:

    ::

        >>> metadataEntry.sourcePath
        u'bach/bwv66.6.mxl'

    The metadata payload contains its metadata object:

    ::

        >>> metadataEntry.metadataPayload
        <music21.metadata.RichMetadata object at 0x...>

    And the metadata entry can be parsed:

    ::

        >>> metadataEntry.parse()
        <music21.stream.Score ...>

    '''

    ### INITIALIZER ###

    def __init__(self,
        sourcePath=None,
        number=None,
        metadataPayload=None,
        ):
        self._sourcePath = sourcePath
        self._number = number
        self._metadataPayload = metadataPayload

    ### SPECIAL METHODS ###

    def __getnewargs__(self):
        return (
            self.sourcePath,
            self.metadataPayload,
            self.number,
            )

    def __repr__(self):
        return '<{0}.{1}: {2}>'.format(
            self.__class__.__module__,
            self.__class__.__name__,
            self.corpusPath,
            )

    ### PUBLIC METHODS ###

    def parse(self):
        from music21 import corpus
        if self.number is not None:
            return corpus.parse(self.sourcePath, number=self.number)
        else:
            return corpus.parse(self.sourcePath)

    def show(self, showFormat=None):
        score = self.parse()
        score.show(showFormat)
        
    def search(self, query, field=None):
        return self.metadataPayload.search(query, field)

    ### PUBLIC PROPERTIES ###

    @property
    def corpusPath(self):
        return MetadataBundle.corpusPathToKey(self.sourcePath, self.number)

    @property
    def metadataPayload(self):
        return self._metadataPayload

    @property
    def number(self):
        return self._number

    @property
    def sourcePath(self):
        return self._sourcePath


#------------------------------------------------------------------------------


class MetadataBundle(object):
    r'''
    An object that provides access to, searches within, and stores and loads
    multiple Metadata objects.

    ::

        >>> from music21 import corpus, metadata
        >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
        >>> coreBundle
        <music21.metadata.bundles.MetadataBundle 'core': {14958 entries}>

    ::

        >>> searchResults = coreBundle.search('bach', field='composer')
        >>> searchResults
        <music21.metadata.bundles.MetadataBundle {21 entries}>

    ::

        >>> resultsEntries = searchResults.search('3/4')
        >>> resultsEntries
        <music21.metadata.bundles.MetadataBundle {4 entries}>

    ::

        >>> resultsEntries[0]
        <music21.metadata.bundles.MetadataEntry: bach_choraleAnalyses_riemenschneider007_rntxt>

    ::

        >>> resultsEntries[0].parse()
        <music21.stream.Score ...>

    A metadata bundle can be instantiated via its static methods
    ``fromCoreCorpus()``, ``fromLocalCorpus()`` and ``fromVirtualCorpus()``, as
    well as from a ``Corpus`` instance, or a string indicating which corpus to
    draw from:

    ::

        >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
        >>> localBundle = metadata.MetadataBundle.fromLocalCorpus()
        >>> virtualBundle = metadata.MetadataBundle.fromVirtualCorpus()

    ::

        >>> coreCorpus = corpus.CoreCorpus()
        >>> coreBundle = metadata.MetadataBundle(coreCorpus)
        >>> localCorpus = corpus.LocalCorpus()
        >>> localBundle = metadata.MetadataBundle(localCorpus)
        >>> virtualCorpus = corpus.VirtualCorpus()
        >>> virtualBundle = metadata.MetadataBundle(virtualCorpus)

    ::

        >>> coreBundle = metadata.MetadataBundle('core')
        >>> localBundle = metadata.MetadataBundle('local')
        >>> virtualBundle = metadata.MetadataBundle('virtual')

    The static methods above take the additional step of reading the
    persisted-to-disk metadata bundle file, and caching the result in memory as
    necessary.

    For the others, you'll need to call ``read()``:

    ::

        >>> coreBundle.read()
        <music21.metadata.bundles.MetadataBundle 'core': {14958 entries}>

    Additionally, any two metadata bundles can be operated on together as
    though they were sets, allowing us to build up more complex searches:

    ::

        >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
        >>> bachBundle = coreBundle.search(
        ...     'bach',
        ...     field='composer',
        ...     )
        >>> bachBundle
        <music21.metadata.bundles.MetadataBundle {21 entries}>

    ::

        >>> tripleMeterBundle = coreBundle.search('3/4')
        >>> tripleMeterBundle
        <music21.metadata.bundles.MetadataBundle {2012 entries}>

    ::

        >>> bachBundle.intersection(tripleMeterBundle)
        <music21.metadata.bundles.MetadataBundle {4 entries}>

    Finally, a metadata bundle need not be associated with any corpus at all,
    and can be populated ad hoc:

    ::

        >>> anonymousBundle = metadata.MetadataBundle()
        >>> paths = corpus.CoreCorpus().getMonteverdiMadrigals()[:4]
        >>> failedPaths = anonymousBundle.addFromPaths(
        ...     paths, useMultiprocessing=False)

    ::

        >>> failedPaths
        []

    ::

        >>> anonymousBundle
        <music21.metadata.bundles.MetadataBundle {4 entries}>

    '''

    ### INITIALIZER ###

    def __init__(self, expr=None):
        from music21 import corpus
        self._metadataEntries = {}
        assert isinstance(expr, (str, corpus.corpora.Corpus, type(None)))
        if isinstance(expr, corpus.corpora.Corpus):
            self._name = expr.name
        else:
            self._name = expr

    ### SPECIAL METHODS ###

    def __and__(self, metadataBundle):
        r'''
        Compute the set-wise `and` of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBundle = coreBundle.search('3/4')
            >>> tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2012 entries}>

        ::

            >>> bachBundle & tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {4 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            '__and__',
            )

    def __eq__(self, other):
        '''
        True if `expr` is of the same type, and contains an identical set of
        entries, otherwise false:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )
            >>> bachBundle == beethovenBundle
            False

        ::

            >>> bachBundle == coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            True

        ::

            >>> bachBundle == 'foo'
            False

        '''
        if type(self) == type(other):
            if self._metadataEntries == other._metadataEntries:
                return True
        return False

    def __ge__(self, metadataBundle):
        '''
        True when one metadata bundle is either a superset or an identical set
        to another bundle:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )

        ::

            >>> bachBundle >= bachBundle
            True

        ::

            >>> bachBundle >= beethovenBundle
            False

        ::

            >>> bachBundle >= coreBundle
            False

        ::

            >>> beethovenBundle >= bachBundle
            False

        ::

            >>> beethovenBundle >= beethovenBundle
            True

        ::

            >>> beethovenBundle >= coreBundle
            False

        ::

            >>> coreBundle >= bachBundle
            True

        ::
            >>> coreBundle >= beethovenBundle
            True

        ::

            >>> coreBundle >= coreBundle
            True

        Return boolean.
        '''
        return self._apply_set_predicate(metadataBundle, '__ge__')

    def __getitem__(self, i):
        # TODO: is this an OrderedDict???
        return list(self._metadataEntries.values())[i]

    def __gt__(self, metadataBundle):
        '''
        True when one metadata bundle is either a subset or an identical set to
        another bundle:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )

        ::

            >>> bachBundle > bachBundle
            False

        ::

            >>> bachBundle > beethovenBundle
            False

        ::

            >>> bachBundle > coreBundle
            False

        ::

            >>> beethovenBundle > bachBundle
            False

        ::

            >>> beethovenBundle > beethovenBundle
            False

        ::

            >>> beethovenBundle > coreBundle
            False

        ::

            >>> coreBundle > bachBundle
            True

        ::
            >>> coreBundle > beethovenBundle
            True

        ::

            >>> coreBundle > coreBundle
            False


        Return boolean.
        '''
        return self._apply_set_predicate(metadataBundle, '__gt__')

    def __le__(self, metadataBundle):
        '''
        True when one metadata bundle is either a subset or an identical set to
        another bundle:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )

        ::

            >>> bachBundle <= bachBundle
            True

        ::

            >>> bachBundle <= beethovenBundle
            False

        ::

            >>> bachBundle <= coreBundle
            True

        ::

            >>> beethovenBundle <= bachBundle
            False

        ::

            >>> beethovenBundle <= beethovenBundle
            True

        ::

            >>> beethovenBundle <= coreBundle
            True

        ::

            >>> coreBundle <= bachBundle
            False

        ::
            >>> coreBundle <= beethovenBundle
            False

        ::

            >>> coreBundle <= coreBundle
            True

        Return boolean.
        '''
        return self._apply_set_predicate(metadataBundle, '__le__')

    def __len__(self):
        return len(self._metadataEntries)

    def __lt__(self, metadataBundle):
        '''
        True when one metadata bundle is a subset of another bundle:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )

        ::

            >>> bachBundle < bachBundle
            False

        ::

            >>> bachBundle < beethovenBundle
            False

        ::

            >>> bachBundle < coreBundle
            True

        ::

            >>> beethovenBundle < bachBundle
            False

        ::

            >>> beethovenBundle < beethovenBundle
            False

        ::

            >>> beethovenBundle < coreBundle
            True

        ::

            >>> coreBundle < bachBundle
            False

        ::
            >>> coreBundle < beethovenBundle
            False

        ::

            >>> coreBundle < coreBundle
            False

        Return boolean.
        '''
        return self._apply_set_predicate(metadataBundle, '__lt__')

    def __ne__(self, expr):
        return self != expr

    def __or__(self, metadataBundle):
        r'''
        Compute the set-wise `or` of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )
            >>> beethovenBundle
            <music21.metadata.bundles.MetadataBundle {16 entries}>

        ::

            >>> bachBundle | beethovenBundle
            <music21.metadata.bundles.MetadataBundle {37 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            '__or__',
            )

    def __repr__(self):
        if len(self) == 1:
            status = '{1 entry}'
        else:
            status = '{{{0} entries}}'.format(len(self))
        if self.name is not None:
            status = '{0!r}: '.format(self.name) + status
        return '<{0}.{1} {2}>'.format(
            self.__class__.__module__,
            self.__class__.__name__,
            status,
            )

    def __sub__(self, metadataBundle):
        r'''
        Compute the set-wise `subtraction` of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBundle = coreBundle.search('3/4')
            >>> tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2012 entries}>

        ::

            >>> bachBundle - tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {17 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            '__sub__',
            )

    def __xor__(self, metadataBundle):
        r'''
        Compute the set-wise `exclusive or` of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBundle = coreBundle.search('3/4')
            >>> tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2012 entries}>

        ::

            >>> bachBundle ^ tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2025 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            '__xor__',
            )

    ### PRIVATE METHODS ###

    def _apply_set_operation(self, metadataBundle, operator):
        assert isinstance(metadataBundle, type(self))
        selfKeys = set(self._metadataEntries.keys())
        otherKeys = set(metadataBundle._metadataEntries.keys())
        resultKeys = getattr(selfKeys, operator)(otherKeys)
        resultBundle = type(self)()
        for key in resultKeys:
            if key in self._metadataEntries:
                metadataEntry = self._metadataEntries[key]
            else:
                metadataEntry = metadataBundle._metadataEntries[key]
            resultBundle._metadataEntries[key] = metadataEntry
        return resultBundle

    def _apply_set_predicate(self, metadataBundle, predicate):
        assert isinstance(metadataBundle, type(self))
        selfKeys = set(self._metadataEntries.keys())
        otherKeys = set(metadataBundle._metadataEntries.keys())
        return getattr(selfKeys, predicate)(otherKeys)

    ### PUBLIC PROPERTIES ###

    @property
    def corpus(self):
        r'''
        The `corpus.corpora.Corpus` object associated with the metadata
        bundle's name.

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
            >>> coreBundle
            <music21.metadata.bundles.MetadataBundle 'core': {14958 entries}>

        ::

            >>> coreBundle.corpus
            <music21.corpus.corpora.CoreCorpus>

        '''
        from music21 import corpus
        if self.name is None:
            return None
        return corpus.corpora.Corpus.fromName(self.name)

    @property
    def filePath(self):
        r'''
        The filesystem name of the cached metadata bundle, if the metadata
        bundle's name is not None.
        '''
        if self.name is None:
            return None
        if self.name in ('virtual', 'core'):
            filePath = os.path.join(
                common.getMetadataCacheFilePath(),
                self.name + '.json',
                )
        elif self.name == 'local':
            # write in temporary dir
            filePath = os.path.join(
                environLocal.getRootTempDir(),
                self.name + '.json',
                )
        else:
            filePath = os.path.join(
                environLocal.getRootTempDir(),
                'local-{0}.json'.format(self.name),
                )
        return filePath

    @property
    def name(self):
        r'''
        The name of the metadata bundle.

        Can be 'core', 'local', 'virtual' or None.

        The names 'core', 'local' and 'virtual refer to the core, local and
        virtual corpuses respectively:

        ::

            >>> from music21 import metadata
            >>> metadata.MetadataBundle().name is None
            True

        ::

            >>> metadata.MetadataBundle.fromCoreCorpus().name == 'core'
            True

        Return string or None.
        '''
        return self._name

    ### PUBLIC METHODS ###

    def addFromPaths(
        self,
        paths,
        useCorpus=False,
        useMultiprocessing=True,
        ):
        '''
        Parse and store metadata from numerous files.

        If any files cannot be loaded, their file paths will be collected in a
        list that is returned.

        Returns a list of file paths with errors and stores the extracted
        metadata in `self._metadataEntries`.

        ::

            >>> from music21 import corpus, metadata
            >>> metadataBundle = metadata.MetadataBundle()
            >>> metadataBundle.addFromPaths(
            ...     corpus.getWorkList('bwv66.6'),
            ...     useCorpus=True,
            ...     useMultiprocessing=False,
            ...     )
            []

        ::

            >>> len(metadataBundle._metadataEntries)
            1

        '''
        from music21 import metadata
        jobs = []
        accumulatedResults = []
        accumulatedErrors = []
        if self.filePath is not None and os.path.exists(self.filePath):
            metadataBundleModificationTime = os.path.getctime(self.filePath)
        else:
            metadataBundleModificationTime = time.time()
        environLocal.printDebug([
            'MetadataBundle Modification Time: {0}'.format(
                metadataBundleModificationTime)
            ])
        currentJobNumber = 0
        skippedJobsCount = 0
        for path in paths:
            if not path.startswith('http'):
                path = os.path.abspath(path)
            key = self.corpusPathToKey(path)
            if key in self._metadataEntries and not key.startswith('http'):
                pathModificationTime = os.path.getctime(path)
                if pathModificationTime < metadataBundleModificationTime:
                    skippedJobsCount += 1
                    continue
            currentJobNumber += 1
            job = metadata.MetadataCachingJob(
                path,
                jobNumber=currentJobNumber,
                useCorpus=useCorpus,
                )
            jobs.append(job)
        currentIteration = 0
        environLocal.printDebug('Skipped {0} sources already in cache.'.format(
            skippedJobsCount))
        if useMultiprocessing:
            jobProcessor = metadata.JobProcessor.process_parallel
        else:
            jobProcessor = metadata.JobProcessor.process_serial
        for result in jobProcessor(jobs):
            metadata.JobProcessor._report(
                len(jobs),
                result['remainingJobs'],
                result['filePath'],
                len(accumulatedErrors),
                )
            currentIteration += 1
            accumulatedResults.extend(result['metadataEntries'])
            accumulatedErrors.extend(result['errors'])
            for metadataEntry in result['metadataEntries']:
                self._metadataEntries[metadataEntry.corpusPath] = metadataEntry
            if (currentIteration % 50) == 0:
                self.write()
        self.validate()
        self.write()
        return accumulatedErrors

    def clear(self):
        r'''
        Clear all keys in a metadata bundle:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()
            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> bachBundle.clear()
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {0 entries}>

        Return none.
        '''
        self._metadataEntries.clear()

    @staticmethod
    def corpusPathToKey(filePath, number=None):
        r'''
        Given a file path or corpus path, return the meta-data path:

        ::

            >>> from music21 import metadata
            >>> mb = metadata.MetadataBundle()
            >>> key = mb.corpusPathToKey('bach/bwv1007/prelude')
            >>> key.endswith('bach_bwv1007_prelude')
            True

        ::

            >>> key = mb.corpusPathToKey('/beethoven/opus59no1/movement1.xml')
            >>> key.endswith('beethoven_opus59no1_movement1_xml')
            True

        '''
        if 'corpus' in filePath or 'music21' in filePath:
            # get filePath after corpus
            corpusPath = filePath.split('corpus')[-1]
        else:
            corpusPath = filePath
        if corpusPath.startswith(os.sep):
            corpusPath = corpusPath[1:]
        corpusPath = corpusPath.replace('/', '_')
        corpusPath = corpusPath.replace(os.sep, '_')
        corpusPath = corpusPath.replace('.', '_')
        # append name to metadata path
        if number is not None:
            return '{0}_{1}'.format(corpusPath, number)
        return corpusPath

    def delete(self):
        r'''
        Delete the filesystem cache of a named metadata bundle.

        Does not delete the in-memory metadata bundle.

        Return none.
        '''
        if self.filePath is not None:
            if os.path.exists(self.filePath):
                os.remove(self.filePath)
        return self

    def difference(self, metadataBundle):
        r'''
        Compute the set-wise difference of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBundle = coreBundle.search('3/4')
            >>> tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2012 entries}>

        ::

            >>> bachBundle.difference(tripleMeterBundle)
            <music21.metadata.bundles.MetadataBundle {17 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            'difference',
            )

    @classmethod
    def fromCoreCorpus(cls):
        r'''
        Return a metadata bundle for the core corpus.

        Read from disk and cache it in memory if the bundle doesn't already
        exist, otherwise pull from memory:

        ::

            >>> from music21 import metadata
            >>> coreCorpusA = metadata.MetadataBundle.fromCoreCorpus()
            >>> coreCorpusB = metadata.MetadataBundle.fromCoreCorpus()
            >>> coreCorpusA is coreCorpusB
            True

        '''
        from music21.corpus import corpora
        corpusName = 'core'
        if corpusName in corpora.Corpus._metadataBundles \
            and corpora.Corpus._metadataBundles[corpusName]:
            return corpora.Corpus._metadataBundles[corpusName]
        bundle = cls(corpusName).read()
        corpora.Corpus._metadataBundles[corpusName] = bundle
        return bundle

    @classmethod
    def fromLocalCorpus(cls, name=None):
        r'''
        Return a metadata bundle for the local corpus.

        Read from disk and cache it in memory if the bundle doesn't already
        exist, otherwise pull from memory:

        ::

            >>> from music21 import metadata
            >>> localCorpusA = metadata.MetadataBundle.fromLocalCorpus()
            >>> localCorpusB = metadata.MetadataBundle.fromLocalCorpus()
            >>> localCorpusA is localCorpusB
            True

        '''
        from music21.corpus import corpora
        if name is None or name == 'local':
            corpusName = 'local'
        else:
            corpusName = 'local-{0}'.format(name)
        if corpusName in corpora.Corpus._metadataBundles and \
            corpora.Corpus._metadataBundles[corpusName] is not None:
            return corpora.Corpus._metadataBundles[corpusName]
        bundle = cls(corpusName).read()
        corpora.Corpus._metadataBundles[corpusName] = bundle
        return bundle

    @classmethod
    def fromVirtualCorpus(cls):
        r'''
        Return a metadata bundle for the virtual corpus.

        Read from disk and cache it in memory if the bundle doesn't already
        exist, otherwise pull from memory:

        ::

            >>> from music21 import metadata
            >>> virtualCorpusA = metadata.MetadataBundle.fromVirtualCorpus()
            >>> virtualCorpusB = metadata.MetadataBundle.fromVirtualCorpus()
            >>> virtualCorpusA is virtualCorpusB
            True

        '''
        from music21.corpus import corpora
        corpusName = 'virtual'
        if corpusName in corpora.Corpus._metadataBundles and \
            corpora.Corpus._metadataBundles[corpusName]:
            return corpora.Corpus._metadataBundles[corpusName]
        bundle = cls(corpusName).read()
        corpora.Corpus._metadataBundles[corpusName] = bundle
        return bundle

    def intersection(self, metadataBundle):
        r'''
        Compute the set-wise intersection of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBundle = coreBundle.search('3/4')
            >>> tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2012 entries}>

        ::

            >>> bachBundle.intersection(tripleMeterBundle)
            <music21.metadata.bundles.MetadataBundle {4 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            'intersection',
            )

    def isdisjoint(self, metadataBundle):
        r'''
        True if the set of keys in one metadata bundle are disjoint with
        the set of keys in another:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )
            >>> beethovenBundle
            <music21.metadata.bundles.MetadataBundle {16 entries}>

        ::

            >>> bachBundle.isdisjoint(beethovenBundle)
            True

        ::

            >>> tripleMeterBundle = coreBundle.search('3/4')
            >>> tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2012 entries}>

        ::

            >>> bachBundle.isdisjoint(tripleMeterBundle)
            False

        Return boolean.
        '''
        return self._apply_set_predicate(metadataBundle, 'isdisjoint')

    def issubset(self, metadataBundle):
        r'''
        True if the set of keys in one metadata bundle are a subset of
        the keys in another:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBachBundle = bachBundle.search('3/4')
            >>> tripleMeterBachBundle
            <music21.metadata.bundles.MetadataBundle {4 entries}>

        ::

            >>> tripleMeterBachBundle.issubset(bachBundle)
            True

        ::

            >>> bachBundle.issubset(tripleMeterBachBundle)
            False

        Return boolean.
        '''
        return self._apply_set_predicate(metadataBundle, 'issubset')

    def issuperset(self, metadataBundle):
        r'''
        True if the set of keys in one metadata bundle are a superset of
        the keys in another:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBachBundle = bachBundle.search('3/4')
            >>> tripleMeterBachBundle
            <music21.metadata.bundles.MetadataBundle {4 entries}>

        ::

            >>> tripleMeterBachBundle.issuperset(bachBundle)
            False

        ::

            >>> bachBundle.issuperset(tripleMeterBachBundle)
            True

        Return boolean.
        '''
        return self._apply_set_predicate(metadataBundle, 'issuperset')

    @staticmethod
    def listSearchFields():
        r'''
        List all available search field names:

        ::

            >>> for field in metadata.MetadataBundle.listSearchFields():
            ...     field
            ...
            'alternativeTitle'
            'ambitus'
            'composer'
            'date'
            'keySignatureFirst'
            'keySignatures'
            'localeOfComposition'
            'movementName'
            'movementNumber'
            'noteCount'
            'number'
            'opusNumber'
            'pitchHighest'
            'pitchLowest'
            'quarterLength'
            'tempoFirst'
            'tempos'
            'timeSignatureFirst'
            'timeSignatures'
            'title'

        '''
        from music21 import metadata
        return tuple(sorted(metadata.RichMetadata._searchAttributes))

    def read(self, filePath=None):
        r'''
        Load cached metadata from the file path suggested by the name of this
        MetadataBundle ('core', 'local', or 'virtual').

        If a specific filepath is given with the `filePath` keyword, attempt to
        load cached metadata from the file at that location.

        If `filePath` is None, and `self.filePath` is also None, do nothing.

        ::

            >>> from music21 import metadata
            >>> virtualBundle = metadata.MetadataBundle('virtual').read()

        If a metadata is unnamed, and no file path is specified, an exception
        will be thrown:

        ::

            >>> anonymousBundle = metadata.MetadataBundle().read()
            Traceback (most recent call last):
            MetadataException: Unnamed MetadataBundles have no default file path to read from.

        '''
        timer = common.Timer()
        timer.start()
        if filePath is None:
            filePath = self.filePath
        if filePath is None and self.name is None:
            raise exceptions21.MetadataException(
                'Unnamed MetadataBundles have no default file path to read '
                'from.')
        if not os.path.exists(filePath):
            environLocal.printDebug('no metadata found for: {0!r}; '
                'try building cache with corpus.cacheMetadata({1!r})'.format(
                    self.name, self.name))
            return self
        jst = freezeThaw.JSONThawer(self)
        jst.jsonRead(filePath)
        environLocal.printDebug([
            'MetadataBundle: loading time:',
            self.name,
            timer,
            'md items:',
            len(self._metadataEntries)
            ])
        return self

    def rebuild(self, useMultiprocessing=True):
        r'''
        Rebuild a named bundle from scratch.

        If a bundle is associated with one of music21's corpuses, delete any
        metadata cache on disk, clear the bundle's contents and reload in all
        files from that associated corpus.

        Return the rebuilt metadata bundle.
        '''
        from music21 import corpus
        if self.filePath is None:
            return self
        self.clear()
        self.delete()
        useCorpus = False
        if isinstance(self.corpus, corpus.corpora.CoreCorpus):
            useCorpus = True
        self.addFromPaths(
            self.corpus.getPaths(),
            useCorpus=useCorpus,
            useMultiprocessing=useMultiprocessing,
            )
        return self

    def search(self, query, field=None, fileExtensions=None):
        r'''
        Perform search, on all stored metadata, permit regular expression
        matching.

        ::

            >>> from music21 import corpus, metadata
            >>> workList = corpus.getWorkList('ciconia')
            >>> metadataBundle = metadata.MetadataBundle()
            >>> metadataBundle.addFromPaths(
            ...     workList,
            ...     useCorpus=True,
            ...     useMultiprocessing=False,
            ...     )
            []

        ::

            >>> searchResult = metadataBundle.search(
            ...     'cicon',
            ...     field='composer'
            ...     )
            >>> searchResult
            <music21.metadata.bundles.MetadataBundle {1 entry}>

        ::

            >>> len(searchResult)
            1

        ::

            >>> searchResult[0]
            <music21.metadata.bundles.MetadataEntry: ciconia_quod_jactatur_xml>

        ::

            >>> searchResult = metadataBundle.search(
            ...     'cicon',
            ...     field='composer',
            ...     fileExtensions=('.krn',),
            ...     )
            >>> len(searchResult) # no files in this format
            0

        ::

            >>> searchResult = metadataBundle.search(
            ...     'cicon',
            ...     field='composer',
            ...     fileExtensions=('.xml'),
            ...     )
            >>> len(searchResult)
            1

        '''
        newMetadataBundle = MetadataBundle()
        for key in self._metadataEntries:
            metadataEntry = self._metadataEntries[key]
            # ignore stub entries
            if metadataEntry.metadataPayload is None:
                continue
            if metadataEntry.search(query, field)[0]:
                include = False
                if fileExtensions is not None:
                    for fileExtension in fileExtensions:
                        if metadataEntry.sourcePath.endswith(fileExtension):
                            include = True
                            break
                        elif fileExtension.endswith('xml') \
                            and metadataEntry.sourcePath.endswith(
                                ('mxl', 'mx')):
                            include = True
                            break
                else:
                    include = True
                if include and key not in newMetadataBundle._metadataEntries:
                    newMetadataBundle._metadataEntries[key] = metadataEntry
        return newMetadataBundle

    def symmetric_difference(self, metadataBundle):
        r'''
        Compute the set-wise symmetric differnce of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> tripleMeterBundle = coreBundle.search('3/4')
            >>> tripleMeterBundle
            <music21.metadata.bundles.MetadataBundle {2012 entries}>

        ::

            >>> bachBundle.symmetric_difference(tripleMeterBundle)
            <music21.metadata.bundles.MetadataBundle {2025 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            'symmetric_difference',
            )

    def union(self, metadataBundle):
        r'''
        Compute the set-wise union of two metadata bundles:

        ::

            >>> from music21 import metadata
            >>> coreBundle = metadata.MetadataBundle.fromCoreCorpus()

        ::

            >>> bachBundle = coreBundle.search(
            ...     'bach',
            ...     field='composer',
            ...     )
            >>> bachBundle
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> beethovenBundle = coreBundle.search(
            ...     'beethoven',
            ...     field='composer',
            ...     )
            >>> beethovenBundle
            <music21.metadata.bundles.MetadataBundle {16 entries}>

        ::

            >>> bachBundle.union(beethovenBundle)
            <music21.metadata.bundles.MetadataBundle {37 entries}>

        Emit new metadata bundle.
        '''
        return self._apply_set_operation(
            metadataBundle,
            'union',
            )

    def validate(self):
        r'''
        Validate each metadata entry in a metadata bundle.

        If the entry represents a non-virtual corpus asset, test that its
        source path is locatable on disk.  If not, remove the metadata entry
        from the metadata bundle.
        '''
        timer = common.Timer()
        timer.start()
        environLocal.printDebug(['MetadataBundle: validating...'])
        invalidatedKeys = []
        validatedPaths = set()
        for key, metadataEntry in self._metadataEntries.items():
            # MetadataEntries for core corpus items use a relative path as
            # their source path, always starting with 'music21/corpus'.
            sourcePath = metadataEntry.sourcePath
            if sourcePath in validatedPaths:
                continue
            if sourcePath.startswith('http:'):
                validatedPaths.add(metadataEntry.sourcePath)
                continue
            if not os.path.isabs(sourcePath):
                sourcePath = os.path.abspath(os.path.join(
                    common.getCorpusFilePath(),
                    sourcePath,
                    ))
            if not os.path.exists(sourcePath):
                invalidatedKeys.append(key)
            validatedPaths.add(metadataEntry.sourcePath)
        for key in invalidatedKeys:
            del(self._metadataEntries[key])
        message = 'MetadataBundle: finished validating in {0} seconds.'.format(
            timer)
        environLocal.printDebug(message)
        return len(invalidatedKeys)

    def write(self, filePath=None):
        r'''
        Write the metadata bundle to disk as a JSON file.

        If `filePath` is None, use `self.filePath`.

        Returns the metadata bundle.

        ::

            >>> from music21 import metadata
            >>> bachBundle = metadata.MetadataBundle.fromCoreCorpus().search(
            ...     'bach',
            ...     'composer',
            ...     )
            >>> bachBundle.filePath is None
            True

        ::

            >>> import os
            >>> import tempfile
            >>> tempFilePath = tempfile.mkstemp()[1]
            >>> bachBundle.write(filePath=tempFilePath)
            <music21.metadata.bundles.MetadataBundle {21 entries}>

        ::

            >>> os.remove(tempFilePath)

        '''
        filePath = filePath or self.filePath
        if self.filePath is not None:
            filePath = self.filePath
            environLocal.printDebug(['MetadataBundle: writing:', filePath])
            jsf = freezeThaw.JSONFreezer(self)
            return jsf.jsonWrite(filePath)
        return self


#------------------------------------------------------------------------------


class Test(unittest.TestCase):

    def runTest(self):
        pass


#------------------------------------------------------------------------------


_DOC_ORDER = (
    MetadataBundle,
    )

__all__ = [
    'MetadataEntry',
    'MetadataBundle',
    ]

if __name__ == "__main__":
    import music21
    music21.mainTest(Test)


#------------------------------------------------------------------------------
