'''<b>ClassifyObjects</b> classifies objects into different classes according 
to the value of measurements you choose.
<hr>
This module classifies objects into a number of different bins
according to the value of a measurement (e.g. by size, intensity, shape).
It reports how many objects fall into each class as well as the
percentage of objects that fall into each class. The module requests that
you select the measurement feature to be used to classify your objects and
specify the bins to use. This module requires that you run a measurement
module previous to this module in the pipeline so that the measurement
values can be used to classify the objects. If you are classifying by the
ratio of two measurements, you must put a CalculateRatios module previous
to this module in the pipeline.
<br>
There are two flavors of classification. The first classifies each object
according to the measurements you choose and assigns each object to one
class per measurement. You may specify more than two classification bins per
measurement. 
<br>
The second classifies each object according to two measurements and two
threshold values. The module classifies each object once per measurement
resulting in four possible object classes. The module then stores one
measurement per object, based on the object's class.
'''

#CellProfiler is distributed under the GNU General Public License.
#See the accompanying file LICENSE for details.
#
#Developed by the Broad Institute
#Copyright 2003-2009
#
#Please see the AUTHORS file for credits.
#
#Website: http://www.cellprofiler.org

__version__="$Revision$"

import cellprofiler.preferences as cpprefs

import numpy as np

import cellprofiler.cpmodule as cpm
import cellprofiler.measurements as cpmeas
import cellprofiler.cpimage as cpi
import cellprofiler.settings as cps

BY_SINGLE_MEASUREMENTS = "Single measurements"
BY_TWO_MEASUREMENTS = "Two measurements"
TM_MEAN = "Mean"
TM_MEDIAN = "Median"
TM_CUSTOM = "Custom"

BC_EVEN = "Evenly spaced bins"
BC_CUSTOM = "Custom-defined bins"

M_CATEGORY = "Classify"

class ClassifyObjects(cpm.CPModule):
    category = "Object Processing"
    module_name = "ClassifyObjects"
    variable_revision_number = 1
    def create_settings(self):
        """Create the settings for the module
        
        Create the settings for the module during initialization.
        """
        self.contrast_choice = cps.Choice(
            "Do you want to classify objects by single measurements or "
            "by two measurements taken together?",
            [BY_SINGLE_MEASUREMENTS, BY_TWO_MEASUREMENTS],
            doc="""This setting controls how classifications are recorded:<br>
            <ul><li><i>Single measurements</i>: ClassifyObjects will record
            one classification for each measurement you choose.</li>
            <li><i>Two measurements</i>: ClassifyObjects will allow you to
            choose two measurements. It will record one classification based
            on the two measurements taken together.</li></ul>""")
        
        ############### Single measurement settings ##################
        #
        # A list holding groupings for each of the single measurements
        # to be done
        #
        self.single_measurements = []
        #
        # A count of # of measurements
        #
        self.single_measurement_count = cps.HiddenCount(self.single_measurements)
        #
        # Add one single measurement to start off
        #
        self.add_single_measurement(False)
        #
        # A button to press to get another measurement
        #
        self.add_measurement_button = cps.DoSomething(
            "Add another measurement","Add", self.add_single_measurement)
        #
        ############### Two-measurement settings #####################
        #
        # The object for the contrasting method
        #
        self.object_name = cps.ObjectNameSubscriber(
            "Enter the object name","None",
            doc="""Select the object that you want to measure from the list.
            This should be an object created by a previous module such as
            <b>IdentifyPrimAutomatic</b>, <b>IdentifySecondary</b> or
            <b>IdentifyTertiarySubregion</b>.""")
        #
        # The two measurements for the contrasting method
        #
        def object_fn():
            return self.object_name.value
        self.first_measurement = cps.Measurement(
            "Select the first measurement", object_fn,
            doc="""Select a measurement made on the above object. This is
            the first of two measurements that will be contrasted together.
            The measurement should be one made on the object in a prior
            module.""")
        
        self.first_threshold_method = cps.Choice(
            "How do you want to select the cutoff?",
            [TM_MEAN, TM_MEDIAN, TM_CUSTOM],
            doc="""Objects are classified as being above or below a cutoff
            value for a measurement. You can set this cutoff threshold in one
            of three ways:<br>
            <ul><li><i>Mean</i>: The threshold is set at the mean
            of the measurement's value for all objects in the image set.</li>
            <li><i>Median</i>: The threshold is set at the median of the
            measurement's value for all objects in the image set.</li>
            <li><i>Custom</i>: You specify a custom threshold value.</li></ul>""")
        
        self.first_threshold = cps.Float(
            "Enter the cutoff value",.5,
            doc="""This is the cutoff value separating objects in the two 
            classes.""")
        
        self.second_measurement = cps.Measurement(
            "Select the second measurement", object_fn,
            doc="""Select a measurement made on the above object. This is
            the second of two measurements that will be contrasted together.
            The measurement should be one made on the object in a prior
            module.""")
        
        self.second_threshold_method = cps.Choice(
            "How do you want to select the cutoff?",
            [TM_MEAN, TM_MEDIAN, TM_CUSTOM],
            doc="""Objects are classified as being above or below a cutoff
            value for a measurement. You can set this cutoff threshold in one
            of three ways:<br>
            <ul><li><i>Mean</i>: The threshold is set at the mean
            of the measurement's value for all objects in the image set.</li>
            <li><i>Median</i>: The threshold is set at the median of the
            measurement's value for all objects in the image set.</li>
            <li><i>Custom</i>: You specify a custom threshold value.</li></ul>""")
        
        self.second_threshold = cps.Float(
            "Enter the cutoff value",.5,
            doc="""This is the cutoff value separating objects in the two 
            classes.""")
        
        self.wants_custom_names = cps.Binary(
            "Use custom names for the bins?", False,
            doc="""Check this if you want to specify the names of each bin 
            measurement. If you leave the box unchecked, the module will
            create names based on the measurements (for instance, for
            Intensity_MeanIntensity_Green and Intensity_TotalIntensity_Blue,
            the module generates measurements such as
            Classify_Intensity_MeanIntensity_Green_High_Intensity_TotalIntensity_Low).""")
        
        self.low_low_custom_name = cps.Text(
            "Enter the low-low bin name","low_low",
            doc="""This is the name of the measurement for objects that
            fall below the threshold for both measurements""")
        
        self.low_high_custom_name = cps.Text(
            "Enter the low-high bin name","low_high",
            doc="""This is the name of the measurement for objects whose
            first measurement is below threshold and whose second measurement
            is above threshold""")
        
        self.high_low_custom_name = cps.Text(
            "Enter the high-low bin name","high_low",
            doc="""This is the name of the measurement for objects whose
            first measurement is above threshold and whose second measurement
            is below threshold""")
        
        self.high_high_custom_name = cps.Text(
            "Enter the high-high bin name","high_high",
            doc="""This is the name of the measurement for objects that
            are above the threshold for both measurements""")
        
        self.wants_image = cps.Binary(
            "Save the display as an image?", False,
            doc="""You can save the graph of this classification as an image.
            Check this option to create the image. You can save this image
            using the <b>SaveImages</b> module.""")
        
        self.image_name = cps.ImageNameProvider(
            "Enter the image name","None",
            doc="""This is the name that will be associated with the graph
            image. You can specify this name in a <b>SaveImages</b> module
            if you want to save the image.""")

    def add_single_measurement(self, can_delete = True):
        '''Add a single measurement to the group of single measurements
        
        can_delete - True to include a "remove" button, False if you're not
                     allowed to remove it.
        '''
        group = cps.SettingsGroup()
        group.append("object_name",cps.ObjectNameSubscriber(
            "Enter object name","None",
            doc="""This is the name of the objects to be classified. You can
            choose from objects created by any previous module. See
            <b>IdentifyPrimAutomatic</b>, <b>IdentifySecondary</b> or
            <b>IdentifyTertiarySubregion</b>"""))
        
        def object_fn():
            return group.object_name.value
        group.append("measurement", cps.Measurement(
            "Select measurement",object_fn,
            doc="""Select a measurement made by a previous module. The objects
            will be classified according to their value for this 
            measurement."""))
        group.append("bin_choice", cps.Choice(
            "Do you want evenly spaced bins or custom bins?",
            [BC_EVEN, BC_CUSTOM],
            doc="""You can either specify bins of equal size, bounded by
            upper and lower limits or you can specify custom values for
            each bin threshold. 
            
            <i>Note:</i> Choose "Custom-defined bins" if you want
            two bins with a single threshold. "Evenly spaced bins" creates
            at least three bins, including a bin of objects that fall below
            the lower threshold and a bin of objects that have values above
            the upper threshold."""))
        
        group.append("bin_count", cps.Integer(
            "How many bins?", 3, minval= 3))
        
        group.append("low_threshold", cps.Float(
            "Enter lower threshold", 0,
            doc="""This is the threshold that separates the lowest bin from the
            others. The lower threshold, upper threshold and number of bins
            define the thresholds of bins between the lowest and highest."""))
        
        def min_upper_threshold():
            return group.low_threshold.value + np.finfo(float).eps
        
        group.append("high_threshold", cps.Float(
            "Enter upper threshold", 1,
            minval = cps.NumberConnector(min_upper_threshold),
            doc="""This is the threshold that separates the last bin from
            the others."""))
        
        group.append("custom_thresholds", cps.Text(
            "Enter the custom thresholds separating the values between bins",
            "0,1",
            doc="""
            <i>(Used if custom thresholds is selected)</i><br>
            This setting establishes the threshold values for the
            bins. You should enter one threshold between each bin, separating
            thresholds with commas (for example, "0.3, 1.5, 2.1" for four bins).
            The module will create one more bin than there are thresholds."""))
        
        group.append("wants_custom_names", cps.Binary(
            "Give each bin a name?", False,
            doc="""This option lets you assign custom names to the measurements
            for each bin. If you leave this unchecked, the module will
            assign names based on the measurements and the bin number."""))
        
        group.append("bin_names", cps.Text(
            "Enter the bin names separated by commas","None",
            doc="""
            <i>(Used if user wants to name the bins)</i><br>
            Enter names for each of the bins with commas in-between.
            An example for three bins might be, "First,Second,Third"."""))
        
        group.append("wants_images", cps.Binary(
            "Save an image of the objects classified by their measurements?",
            False))
        
        group.append("image_name", cps.ImageNameProvider(
            "Enter image name", "ClassifiedNuclei"))
        
        group.can_delete = can_delete
        def number_of_bins():
            '''Return the # of bins in this classification'''
            if group.bin_choice == BC_EVEN:
                return group.bin_count.value
            else:
                return len(group.custom_thresholds.value.split(","))+1
        group.number_of_bins = number_of_bins
        def bin_feature_names():
            '''Return the feature names for each bin'''
            if group.wants_custom_names:
                return [name.strip() 
                        for name in group.bin_names.value.split(",")]
            return ['_'.join((group.measurement.value,
                              'Bin_%d'%(i+1)))
                    for i in range(number_of_bins())]
        group.bin_feature_names = bin_feature_names
        
        def validate_group():
            bin_name_count = len(bin_feature_names())
            bin_count = number_of_bins()
            if bin_name_count != number_of_bins():
                raise cps.ValidationError(
                    "The number of bin names (%d) does not match the number of bins (%d)." %
                    (bin_name_count, bin_count), group.bin_names)
            if group.bin_choice == BC_CUSTOM:
                try:
                    [float(x.strip()) 
                     for x in group.custom_thresholds.value.split(",")]
                except ValueError:
                    raise cps.ValidationError(
                        'Custom thresholds must be a comma-separated list '
                        'of numbers (example: "1.0, 2.3, 4.5")',
                        group.custom_thresholds)
        group.validate_group = validate_group
        
        if can_delete:
            group.remove_settings_button = cps.RemoveSettingButton(
                "Remove the above measurement", "Remove", 
                self.single_measurements, group)
        self.single_measurements.append(group)
    
    def settings(self):
        result = [self.contrast_choice, self.single_measurement_count]
        result += reduce(lambda x,y: x+y,
                         [group.unpack_group() 
                          for group in self.single_measurements])
        result += [self.object_name, self.first_measurement,
                   self.first_threshold_method, self.first_threshold,
                   self.second_measurement, self.second_threshold_method,
                   self.second_threshold, self.wants_custom_names,
                   self.low_low_custom_name, self.low_high_custom_name,
                   self.high_low_custom_name, self.high_high_custom_name,
                   self.wants_image, self.image_name]
        return result
    
    def visible_settings(self):
        result = [self.contrast_choice]
        if self.contrast_choice == BY_TWO_MEASUREMENTS:
            #
            # Visible settings if there are two measurements
            #
            result += [self.object_name]
            for measurement_setting, threshold_method_setting, threshold_setting \
                in ((self.first_measurement, self.first_threshold_method,
                     self.first_threshold),
                    (self.second_measurement, self.second_threshold_method,
                     self.second_threshold)):
                result += [measurement_setting, threshold_method_setting]
                if threshold_method_setting == TM_CUSTOM:
                    result += [threshold_setting]
            result += [self.wants_custom_names]
            if self.wants_custom_names:
                result += [self.low_low_custom_name, self.low_high_custom_name,
                           self.high_low_custom_name, self.high_high_custom_name]
            result += [self.wants_image]
            if self.wants_image:
                result += [self.image_name]
        else:
            #
            # Visible results per single measurement
            #
            for group in self.single_measurements:
                result += [group.object_name, group.measurement,
                           group.bin_choice]
                if group.bin_choice == BC_EVEN:
                    result += [group.bin_count, group.low_threshold,
                               group.high_threshold]
                else:
                    result += [group.custom_thresholds]
                result += [group.wants_custom_names]
                if group.wants_custom_names:
                    result += [group.bin_names]
                result += [group.wants_images]
                if group.wants_images:
                    result += [group.image_name]
                if group.can_delete:
                    result += [group.remove_settings_button]
            result += [self.add_measurement_button]
        return result
    
    def is_interactive(self):
        '''Indicate that this module's display does not interact with the user'''
        return False
    
    def run(self, workspace):
        """Classify the objects in the image set"""
        if self.contrast_choice == BY_SINGLE_MEASUREMENTS:
            if workspace.frame:
                workspace.display_data.labels = []
                workspace.display_data.bins = []
                workspace.display_data.values = []
            for group in self.single_measurements:
                self.run_single_measurement(group, workspace)
        elif self.contrast_choice == BY_TWO_MEASUREMENTS:
            self.run_two_measurements(workspace)
        else:
            raise ValueError("Invalid classification method: %s"%
                             self.contrast_choice.value)
    
    def display(self, workspace):
        if self.contrast_choice == BY_TWO_MEASUREMENTS:
            self.display_two_measurements(workspace)
        else:
            self.display_single_measurement(workspace)
                
    def get_feature_name_matrix(self):
        '''Get a 2x2 matrix of feature names for two measurements'''
        if self.wants_custom_names:
            return np.array([[self.low_low_custom_name.value,
                              self.low_high_custom_name.value],
                             [self.high_low_custom_name.value,
                              self.high_high_custom_name.value]])
        else:
            m1 = self.first_measurement.value
            m2 = self.second_measurement.value
            return np.array([["_".join((m1,a1,m2,a2)) for a2 in ("low","high")]
                             for a1 in ("low","high")])
        
    def run_two_measurements(self, workspace):
        measurements = workspace.measurements
        in_high_class = []
        saved_values = []
        for feature, threshold_method, threshold in (
            (self.first_measurement, self.first_threshold_method, 
             self.first_threshold),
            (self.second_measurement, self.second_threshold_method,
             self.second_threshold)):
            values = measurements.get_current_measurement(
                self.object_name.value, feature.value)
            saved_values.append(values)
            if threshold_method == TM_CUSTOM:
                t = threshold.value
            elif len(values) == 0:
                t = 0
            elif threshold_method == TM_MEAN:
                t = np.mean(values)
            elif threshold_method == TM_MEDIAN:
                t = np.median(values)
            else:
                raise ValueError("Unknown threshold method: %s" %
                                 threshold_method.value)
            in_high_class.append(values >= t)
        feature_names = self.get_feature_name_matrix()
        for i in range(2):
            for j in range(2):
                in_class = ((in_high_class[0].astype(int) == i) &
                            (in_high_class[1].astype(int) == j))
                measurements.add_measurement(self.object_name.value,
                                             "_".join((M_CATEGORY, feature_names[i,j])),
                                             in_class.astype(int))

        objects = workspace.object_set.get_objects(self.object_name.value)
        if self.wants_image:
            class_1, class_2 = in_high_class
            object_codes = class_1.astype(int)+class_2.astype(int)*2 + 1
            object_codes = np.hstack(([0], object_codes))
            labels = object_codes[objects.segmented]
            colors = self.get_colors(4)
            image = colors[labels,:3]
            image = cpi.Image(image,parent_image = objects.parent_image)
            workspace.image_set.add(self.image_name.value, image)
            
        if workspace.frame is not None:
            workspace.display_data.in_high_class=in_high_class
            workspace.display_data.labels = objects.segmented,
            workspace.display_data.saved_values = saved_values
            
    def display_two_measurements(self, workspace):            
        figure = workspace.create_or_find_figure(subplots=(2,2))
        object_name = self.object_name.value
        for i, feature_name in ((0, self.first_measurement.value),
                                (1, self.second_measurement.value)):
            axes = figure.subplot(i,0)
            axes.hist(workspace.display_data.saved_values[i])
            axes.set_xlabel(feature_name)
            axes.set_ylabel("# of %s"%object_name)
        class_1, class_2 = workspace.display_data.in_high_class
        object_codes = class_1.astype(int)+class_2.astype(int)*2 + 1
        object_codes = np.hstack(([0], object_codes))
        labels = object_codes[workspace.display_data.labels]
        figure.subplot_imshow_labels(0,1, labels, title = object_name,
                                     renumber=False)
        #
        # Draw a 4-bar histogram
        #
        axes = figure.subplot(1,1)
        axes.hist(object_codes[1:],bins=4, range=(.5,4.5))
        axes.set_xticks((1,2,3,4))
        axes.set_xticklabels(("low\nlow","high\nlow","low\nhigh","high\nhigh"))
        axes.set_ylabel("# of %s"%object_name)
        colors = self.get_colors(len(axes.patches))
        #
        # The patches are the rectangles in the histogram
        #
        for i, patch in enumerate(axes.patches):
            patch.set_facecolor(colors[i+1,:])
            
    def run_single_measurement(self, group, workspace):
        '''Classify objects based on one measurement'''
        object_name = group.object_name.value
        feature = group.measurement.value
        objects = workspace.object_set.get_objects(object_name)
        measurements = workspace.measurements
        values = measurements.get_current_measurement(object_name, feature)
        if group.bin_choice == BC_EVEN:
            low_threshold = group.low_threshold.value
            high_threshold = group.high_threshold.value
            bin_count = group.bin_count.value
            thresholds = (np.arange(bin_count-1) *
                          (high_threshold - low_threshold)/float(bin_count-2) +
                          low_threshold)
        else:
            thresholds = [float(x.strip()) 
                          for x in group.custom_thresholds.value.split(',')]
        #
        # Put infinities at either end of the thresholds so we can bin the
        # low and high bins
        #
        thresholds = np.hstack(([-np.inf],thresholds,[np.inf]))
        #
        # Do a cross-product of objects and threshold comparisons
        #
        ob_idx,th_idx = np.mgrid[0:len(values),0:len(thresholds)-1]
        bin_hits = ((values[ob_idx] > thresholds[th_idx]) &
                    (values[ob_idx] <= thresholds[th_idx+1]))
        for bin_idx, feature_name in enumerate(group.bin_feature_names()):
            measurement_name = '_'.join((M_CATEGORY, feature_name))
            measurements.add_measurement(object_name, measurement_name,
                                         bin_hits[:,bin_idx])
        if group.wants_images or (workspace.frame is not None):
            colors = self.get_colors(bin_hits.shape[1])
            object_bins = np.sum(bin_hits * th_idx,1)+1
            object_color = np.hstack(([0],object_bins))
            labels = object_color[objects.segmented]
            if group.wants_images:
                image = colors[labels,:3]
                workspace.image_set.add(
                    group.image_name.value, 
                    cpi.Image(image, parent_image = objects.parent_image))
            
            if workspace.frame is not None:
                workspace.display_data.bins.append(object_bins)
                workspace.display_data.labels.append(labels)
                workspace.display_data.values.append(values)
    
    def display_single_measurement(self, workspace):
        '''Display an array of single measurements'''
        figure = workspace.create_or_find_figure(
            subplots=(3,len(self.single_measurements)))
        for i, group in enumerate(self.single_measurements):
            bin_hits = workspace.display_data.bins[i]
            labels = workspace.display_data.labels[i]
            values = workspace.display_data.values[i]
            #
            # A histogram of the values
            #
            axes = figure.subplot(0,i)
            axes.hist(values)
            axes.set_xlabel(group.measurement.value)
            axes.set_ylabel("# of %s"%group.object_name.value)
            #
            # A histogram of the labels yielding the bins
            #
            axes = figure.subplot(1,i)
            axes.hist(bin_hits, bins=group.number_of_bins(),
                      range=(.5,group.number_of_bins()+.5))
            axes.set_xticks(np.arange(1,group.number_of_bins()+1))
            if group.wants_custom_names:
                axes.set_xticklabels(group.bin_names.value.split(","))
            axes.set_xlabel(group.measurement.value)
            axes.set_ylabel("# of %s"%group.object_name.value)
            colors = self.get_colors(len(axes.patches))
            for j, patch in enumerate(axes.patches):
                patch.set_facecolor(colors[j+1,:])
            #
            # The labels matrix
            #
            figure.subplot_imshow_labels(2,i, labels, 
                                         title = group.object_name.value,
                                         renumber=False)
            
    def get_colors(self, count):
        '''Get colors used for two-measurement labels image'''
        import matplotlib.cm as cm
        cmap=cm.get_cmap(cpprefs.get_default_colormap())
        #
        # Trick the colormap into divulging the values used.
        #
        sm = cm.ScalarMappable(cmap=cmap)
        colors = sm.to_rgba(np.arange(count)+1)
        return np.vstack((np.zeros(colors.shape[1]), colors))
        
    def prepare_settings(self, setting_values):
        """Do any sort of adjustment to the settings required for the given values
        
        setting_values - the values for the settings just prior to mapping
                         as done by set_settings_from_values
        This method allows a module to specialize itself according to
        the number of settings and their value. For instance, a module that
        takes a variable number of images or objects can increase or decrease
        the number of relevant settings so they map correctly to the values."""
        
        single_measurement_count = int(setting_values[1])
        if single_measurement_count < len(self.single_measurements):
            del self.single_measurements[single_measurement_count:]
        while single_measurement_count > len(self.single_measurements):
            self.add_single_measurement(True)
            
    def validate_module(self, pipeline):
        if self.contrast_choice == BY_SINGLE_MEASUREMENTS:
            for group in self.single_measurements:
                group.validate_group()
                
    def upgrade_settings(self,setting_values,variable_revision_number,
                         module_name,from_matlab):
        '''Adjust setting values if they came from a previous revision
        
        setting_values - a sequence of strings representing the settings
                         for the module as stored in the pipeline
        variable_revision_number - the variable revision number of the
                         module at the time the pipeline was saved. Use this
                         to determine how the incoming setting values map
                         to those of the current module version.
        module_name - the name of the module that did the saving. This can be
                      used to import the settings from another module if
                      that module was merged into the current module
        from_matlab - True if the settings came from a Matlab pipeline, False
                      if the settings are from a CellProfiler 2.0 pipeline.
        
        Overriding modules should return a tuple of setting_values,
        variable_revision_number and True if upgraded to CP 2.0, otherwise
        they should leave things as-is so that the caller can report
        an error.
        '''
        if (from_matlab and 
            module_name == 'ClassifyObjectsByTwoMeasurements' and
            variable_revision_number == 2):
            category = [None,None]
            feature_name = [None,None]
            image_name = [None, None]
            size_scale = [None, None]
            separator = [None, None]
            threshold = [None, None]
            measurement = [None, None]
            (object_name, category[0], feature_name[0], image_name[0],
             size_scale[0], category[1], feature_name[1], image_name[1],
             size_scale[1], separator[0], separator[1], labels,
             save_colored_objects) = setting_values
            for i in range(2):
                measurement[i] = category[i]+'_'+feature_name[i]
                if len(image_name[i]) > 0:
                    measurement[i] += '_' + image_name[i]
                if len(size_scale[i]) > 0:
                    measurement[i] += '_' + size_scale[i]
                threshold[i] = ".5"
                if separator[i] not in (TM_MEAN, TM_MEDIAN):
                    threshold[i] = separator[i]
                    separator[i] = TM_CUSTOM
            split_labels = [x.strip() for x in labels.split(',')]
            if len(split_labels) < 4:
                split_labels += ["None"]*(4-len(split_labels))
            setting_values = [
                BY_TWO_MEASUREMENTS, "1", "None", "None", BC_EVEN,
                "3", "0", "1", "0,1",cps.NO,"First,Second,Third",
                cps.NO,"ClassifiedNuclei",
                object_name, measurement[0], separator[0], threshold[0],
                measurement[1], separator[1], threshold[1],
                cps.NO if labels == cps.DO_NOT_USE else cps.YES,
                split_labels[0], split_labels[1], split_labels[2],
                split_labels[3],
                cps.NO if save_colored_objects == cps.DO_NOT_USE else cps.YES,
                save_colored_objects]
            from_matlab = False
            module_name = self.module_name
            variable_revision_number = 1
        if (from_matlab and module_name == 'ClassifyObjects' and
            variable_revision_number == 8):
            (object_name, category, feature_name, image_name, size_scale,
             bin_type, bin_specifications, labels, 
             save_colored_objects) = setting_values
            measurement = category+'_'+feature_name
            if len(image_name) > 0:
                measurement += '_' + image_name
            if len(size_scale) > 0:
                measurement += '_' + size_scale
            bin_count = "3"
            low_threshold = "0"
            high_threshold = "1"
            custom_bins = "0,1"
            if bin_type == BC_EVEN:
                pieces = bin_specifications.split(',')
                bin_count = pieces[0]
                if len(pieces) > 1:
                    low_threshold = pieces[1]
                if len(pieces) > 2:
                    high_threshold = pieces[2]
            else:
                custom_bins = bin_specifications
            wants_labels = cps.NO if labels == cps.DO_NOT_USE else cps.YES
            setting_values = [
                BY_SINGLE_MEASUREMENTS, "1", object_name, measurement,
                bin_type, bin_count, low_threshold, high_threshold,
                custom_bins, wants_labels, labels,
                cps.NO if save_colored_objects == cps.DO_NOT_USE else cps.YES,
                save_colored_objects,
                object_name, "None", TM_MEAN, ".5", "None", TM_MEAN, ".5", 
                cps.NO, "LowLow","HighLow","LowHigh","HighHigh", cps.NO,
                "ClassifiedNuclei"]
            from_matlab = False
            variable_revision_number = 1
            
        return setting_values, variable_revision_number, from_matlab

    def get_measurement_columns(self, pipeline):
        columns = []
        if self.contrast_choice == BY_SINGLE_MEASUREMENTS:
            for group in self.single_measurements:
                columns += [(group.object_name.value,
                             '_'.join((M_CATEGORY,feature_name)),
                             cpmeas.COLTYPE_INTEGER)
                            for feature_name in group.bin_feature_names()]
        else:
            names = self.get_feature_name_matrix()
            columns += [(self.object_name.value,
                         '_'.join((M_CATEGORY, name)),
                         cpmeas.COLTYPE_INTEGER)
                        for name in names.flatten()]
        return columns
    
    def get_categories(self,pipeline, object_name):
        """Return the categories of measurements that this module produces
        
        object_name - return measurements made on this object (or 'Image' for image measurements)
        """
        if ((self.contrast_choice == BY_SINGLE_MEASUREMENTS and
             object_name in [group.object_name.value 
                             for group in self.single_measurements]) or
            (self.contrast_choice == BY_TWO_MEASUREMENTS and
             object_name == self.object_name)):
            return [ M_CATEGORY]
                
        return []
      
    def get_measurements(self, pipeline, object_name, category):
        """Return the measurements that this module produces
        
        object_name - return measurements made on this object (or 'Image' for image measurements)
        category - return measurements made in this category
        """
        if category != M_CATEGORY:
            return []
        if self.contrast_choice == BY_SINGLE_MEASUREMENTS:
            result = []
            for group in self.single_measurements:
                if group.object_name == object_name:
                    result += group.bin_feature_names()
            return result
        elif (self.contrast_choice == BY_TWO_MEASUREMENTS and
              self.object_name == object_name):
            return self.get_feature_name_matrix().flatten().tolist()
        return []
