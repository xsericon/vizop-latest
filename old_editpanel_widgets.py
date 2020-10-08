# Following are ControlPanel widget sets defined for objects in an FT. Might be needed later

# Widgets = {
# 'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
# 	'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
# 	'Sci': CheckboxWidget(SizerPos=(1,0), SizerSpan=(1,1), Text=_('Sci')),
# 	'SigFigs': IntSpinboxWidget(SizerPos=(1,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
# 	'SigFigsLabel': StaticTextWidget(SizerPos=(1,2), SizerSpan=(1,1), Text=_('sig.figs')),
# 	'Value': TextCtrlWidget(SizerPos=(1,3), SizerSpan=(1,1)),
# 	'Unit': ChoiceWidget(SizerPos=(1,4), SizerSpan=(1,1)) }

	# # define group of iWindow widgets for numerical values
	# Widgets = {
	# 'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
	# 'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
	# 'Constant': ChoiceWidget(SizerPos=(0,3), SizerSpan=(1,1)),
	# 'New': NormalButtonWidget(SizerPos=(1,3), SizerSpan=(1,1), Text=_('New')),
	# 'Edit': NormalButtonWidget(SizerPos=(1,4), SizerSpan=(1,1), Text=_('Edit')),
	# 'Sci': CheckboxWidget(SizerPos=(2,0), SizerSpan=(1,1), Text=_('Sci')),
	# 'SigFigs': IntSpinboxWidget(SizerPos=(2,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
	# 'SigFigsLabel': StaticTextWidget(SizerPos=(2,2), SizerSpan=(1,1), Text=_('sig.figs')),
	# 'Value': StaticTextWidget(SizerPos=(2,3), SizerSpan=(1,1)),
	# 'Unit': StaticTextWidget(SizerPos=(2,4), SizerSpan=(1,1)) }


	# define group of iWindow widgets for formulae
	# Widgets = {
	# 'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
	# 'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
	# 'SetFormula': NormalButtonWidget(SizerPos=(1,3), SizerSpan=(1,1), Text=_('Set formula')),
	# 'Sci': CheckboxWidget(SizerPos=(1,0), SizerSpan=(1,1), Text=_('Sci')),
	# 'SigFigs': IntSpinboxWidget(SizerPos=(1,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
	# 'SigFigsLabel': StaticTextWidget(SizerPos=(1,2), SizerSpan=(1,1), Text=_('sig.figs')),
	# 'Value': StaticTextWidget(SizerPos=(1,3), SizerSpan=(1,1)),
	# 'Unit': StaticTextWidget(SizerPos=(1,4), SizerSpan=(1,1)) }


	# # define group of iWindow widgets
	# Widgets = {
	# 	'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
	# 	'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
	# 	'SetFormula': NormalButtonWidget(SizerPos=(1,3), SizerSpan=(1,1), Text=_('Set up matrix')),
	# 	'Sci': CheckboxWidget(SizerPos=(1,0), SizerSpan=(1,1), Text=_('Sci')),
	# 	'SigFigs': IntSpinboxWidget(SizerPos=(1,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
	# 	'SigFigsLabel': StaticTextWidget(SizerPos=(1,2), SizerSpan=(1,1), Text=_('sig.figs')),
	# 	'Value': StaticTextWidget(SizerPos=(1,3), SizerSpan=(1,1)),
	# 	'Unit': StaticTextWidget(SizerPos=(1,4), SizerSpan=(1,1)) }

	# define group of iWindow widgets
	# Widgets = {
	# 	'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
	# 	'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
	# 	'Sci': CheckboxWidget(SizerPos=(1,0), SizerSpan=(1,1), Text=_('Sci')),
	# 	'SigFigs': IntSpinboxWidget(SizerPos=(1,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
	# 	'SigFigsLabel': StaticTextWidget(SizerPos=(1,2), SizerSpan=(1,1), Text=_('sig.figs')),
	# 	'Value': TextCtrlWidget(SizerPos=(1,3), SizerSpan=(1,1)),
	# 	'Unit': ChoiceWidget(SizerPos=(1,4), SizerSpan=(1,1)) }

	# define group of iWindow widgets
	# Widgets = {
	# 	'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
	# 	'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
	# 	'SelectParent': NormalButtonWidget(SizerPos=(0,3), SizerSpan=(1,2), Text=_('Select source')),
	# 	'New': NormalButtonWidget(SizerPos=(1,3), SizerSpan=(1,1), Text=_('Show')),
	# 	'Edit': NormalButtonWidget(SizerPos=(1,4), SizerSpan=(1,1), Text=_('Go to')),
	# 	'Sci': CheckboxWidget(SizerPos=(2,0), SizerSpan=(1,1), Text=_('Sci')),
	# 	'SigFigs': IntSpinboxWidget(SizerPos=(2,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
	# 	'SigFigsLabel': StaticTextWidget(SizerPos=(2,2), SizerSpan=(1,1), Text=_('sig.figs')),
	# 	'Value': StaticTextWidget(SizerPos=(2,3), SizerSpan=(1,1)),
	# 	'Unit': StaticTextWidget(SizerPos=(2,4), SizerSpan=(1,1)) }

	# define group of iWindow widgets
	# Widgets = {
	# 	'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
	# 	'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
	# 	'SetDefault': NormalButtonWidget(SizerPos=(1,3), SizerSpan=(1,1), Text=_('Change value')),
	# 	'Sci': CheckboxWidget(SizerPos=(1,0), SizerSpan=(1,1), Text=_('Sci')),
	# 	'SigFigs': IntSpinboxWidget(SizerPos=(1,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
	# 	'SigFigsLabel': StaticTextWidget(SizerPos=(1,2), SizerSpan=(1,1), Text=_('sig.figs')),
	# 	'Value': StaticTextWidget(SizerPos=(1,3), SizerSpan=(1,1)),
	# 	'Unit': StaticTextWidget(SizerPos=(1,4), SizerSpan=(1,1)) }



	# define group of iWindow widgets
	# Widgets = {
	# 	'Label': StaticTextWidget(SizerPos=(0,0), SizerSpan=(1,1), Text=_('Value:') + ' '),
	# 	'Type': ChoiceWidget(SizerPos=(0,1), SizerSpan=(1,2), Choices=NumValueClassHumanNames, DefaultIndex=NumValueClasses.index(type(self))),
	# 	'SelectParent': NormalButtonWidget(SizerPos=(0,3), SizerSpan=(1,2), Text=_('Select source')),
	# 	'New': NormalButtonWidget(SizerPos=(1,3), SizerSpan=(1,1), Text=_('Show')),
	# 	'Edit': NormalButtonWidget(SizerPos=(1,4), SizerSpan=(1,1), Text=_('Go to')),
	# 	'Sci': CheckboxWidget(SizerPos=(2,0), SizerSpan=(1,1), Text=_('Sci')),
	# 	'SigFigs': IntSpinboxWidget(SizerPos=(2,1), SizerSpan=(1,1), DefaultValue=2, MinValue=0, MaxValue=5),
	# 	'SigFigsLabel': StaticTextWidget(SizerPos=(2,2), SizerSpan=(1,1), Text=_('sig.figs')),
	# 	'Value': StaticTextWidget(SizerPos=(2,3), SizerSpan=(1,1)),
	# 	'Unit': StaticTextWidget(SizerPos=(2,4), SizerSpan=(1,1)) }

