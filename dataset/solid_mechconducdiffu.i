# Lily 2026/2/26

[GlobalParams]
  seed = 12345
  displacements = 'disp_x disp_y'
[]

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 75
  ny = 50
  xmin = 0
  xmax = 75
  ymin = 0
  ymax = 50
  elem_type = QUAD4
[]

[Variables]
  # order parameter
  [./eta]
    order = FIRST
    family = LAGRANGE
  [../]

  # solute concentration
  [./c]
    order = FIRST
    family = LAGRANGE
  [../]
  
  # electric overpotential
  [./pot]
    order = FIRST
    family = LAGRANGE
  [../]

 #phi for solid fraction in liquid 
  [./phi]
    order = FIRST
    family = LAGRANGE
  [../] 
  
  [./disp_x]
    order = FIRST
    family = LAGRANGE
  [../]

  [./disp_y]
    order = FIRST
    family = LAGRANGE
  [../]
  
[]

[AuxVariables]
  [./delta_eta]
  [../]
  [./delta_c]
  [../]
  [./delta_pot]
  [../]
  [./gr_c]
   order = CONSTANT
   family = MONOMIAL
  [../]
  # [bnds]
  # []
[]

[ICs]
  [./eta]
    variable = eta
    type = FunctionIC
    function = 'if(x>=0&x<=5,1,0)' #change the function
  [../]
  [./phi]
    variable = phi
    type = FunctionIC
    # function = 'if(x>=0&x<=8,0,if(y<=30&y>=20,0,1))' #model 0-A
    # function = 'if(x>=0&x<=8,0,if(y>=40,0,if(y>20&y<30,0,if(y>=0&y<10,0,1))))'# model 0-B solidmechstructure23,24
    # function = 'if(x>=0&x<=8,0,if(y>=45|y<=5,0,1))'# model 0-c solidmechstructure31 0-c
    # function = 'if(x>=0&x<=8,0,if(y<=35&y>=15,0,1))' #model 1-A solidmechstructure41
    # function = 'if(x>=0&x<=8,0,if(y>=45,0,if(y>10&y<40,0,if(y>=0&y<=5,0,1))))'# model 1-B solidmechstructure51
    function = 'if(x>=0&x<=8,0,if(y>35|y<15,0,1))'# model 1-c solidmechstructure61
  [../]
  [./c]
    variable = c	# lithium ion concentration
    type = FunctionIC
    # function = 'if(x>=0&x<=5,0.1,if(y<=30&y>=20,0.8,0.2))'
    # function = 'if(x>=0&x<=5,0.1,if(y>=40,0.8,if(y>20&y<30,0.2,if(y>0&y<10,0.8,0.2))))'
    # function = 'if(x>=0&x<=5,0.1,if(y>=45|y<=5,0.8,0.2))'# model 0-c solidmechstructure31 0-c
    # function = 'if(x>=0&x<=5,0.1,if(y<=35&y>=15,0.8,0.2))' #model 1-A solidmechstructure41
    # function = 'if(x>=0&x<=5,0.1,if(y>=45,0.8,if(y>10&y<40,0.8,if(y>=0&y<=5,0.8,0.2))))'# model 1-B solidmechstructure51
    function = 'if(x>=0&x<=5,0.1,if(y>35|y<15,0.8,0.2))'# model 1-c solidmechstructure61
  [../]
[]

[BCs]
  [./left_pot]
    type = DirichletBC
    variable = 'pot'
    boundary = 'left'
    value = -0.45
  [../]
  [./right_pot]
    type = DirichletBC
    variable = 'pot'
    boundary = 'right'
    value = 0
  [../]
  [./right_comp]	# connected to the electrolyte
    type = DirichletBC
    variable = 'c'
    boundary = 'right'
    value = 0.8
  [../]
  [./left_x]
    type = DirichletBC
    variable = disp_x
    boundary = left
    value = 0
  [../]
  [./right_x]
    type = DirichletBC
    variable = disp_x
    boundary = right
    value = 0
  [../]
[]
[Materials]
  [./scale]
    type = GenericConstantMaterial
    prop_names = 'length_scale energy_scale time_scale'
    prop_values = '1e6 6.24150943e18 1e3'
  [../]
  [./constants]
    type = GenericConstantMaterial
    prop_names  = 'c_s c_0 valency molar_vol Faraday RT alpha'
    # prop_values = '7.69e4 1e3 1 2.2e-5 96485 2494.2 0.5'
    prop_values = '7.69e4 1e3 1 2.2e-5 96485 2494.2 0.5'
  [../]
  [./system_constants]
    type = GenericConstantMaterial
    prop_names  = 'Meo Mlo Mso L1o L1o_phi L2o ko ko_phi S1o S2o S3o'
    prop_values = '1e-13 5e-13 3e-13 0.25 0.0001 0.1 1e-11 1e-11 1e7 1.19 10'
  [../]
  [./material_constants]
    type = GenericConstantMaterial
    prop_names  = 'fo Al As Bl Bs Cl Cs cleq cseq'	# j/mol
    prop_values = '0.01 1 3 2 1.5 0 0 0.6 0.4'
  [../]
  # mechanical
  [./mechanical_constants]
    type = GenericConstantMaterial
    prop_names = 'Emo Eeo Efo nu V1 V2 V3'
    prop_values = '4.9 0.982 300 0.36 -0.866e-3 -0.773e-3 -0.529e-3'
  [../]
  [./nu_eff]
    type = ParsedMaterial
    property_name = nu_eff
    expression = 'nu'
    material_property_names = 'nu'
    outputs = exodus
  [../]
  [./Em]
    type = ParsedMaterial
    expression = '((energy_scale)/(length_scale)^3)*Emo'
    property_name = Em
    material_property_names = 'Emo length_scale energy_scale'
    outputs = exodus
  [../]
  [./Ee]
    type = ParsedMaterial
    expression = '((energy_scale)/(length_scale)^3)*Eeo'
    property_name = Ee
    material_property_names = 'Eeo length_scale energy_scale'
    outputs = exodus
  [../]
  [./Ef]
    type = ParsedMaterial
    expression = '((energy_scale)/(length_scale)^3)*Efo'
    property_name = Ef
    material_property_names = 'Efo length_scale energy_scale'
    outputs = exodus
  [../]
  [./L1]
    type = ParsedMaterial
    expression = '((length_scale)^3/(energy_scale*time_scale))*L1o'
    property_name = L1
    material_property_names = 'L1o length_scale energy_scale time_scale'
    outputs = exodus
  [../]
  [./L1_phi]
    type = ParsedMaterial
    expression = '((length_scale)^3/(energy_scale*time_scale))*L1o_phi'
    property_name = L1_phi
    material_property_names = 'L1o_phi length_scale energy_scale time_scale'
    outputs = exodus
  [../]
  [./L2]
    type = ParsedMaterial
    expression = 'L2o/time_scale'
    property_name = L2
    material_property_names = 'L2o time_scale'
    outputs = exodus
  [../]
  [./kappa_isotropy]
    type = ParsedMaterial
    property_name = kappa
    expression = '(energy_scale/length_scale)*ko'
    material_property_names = 'ko length_scale energy_scale'
    outputs = exodus
  [../]
  [./kappa_isotropy_phi]
    type = ParsedMaterial
    property_name = kappa_phi
    expression = '(energy_scale/length_scale)*ko_phi'
    material_property_names = 'ko_phi length_scale energy_scale'
    outputs = exodus
  [../]
  # h(eta) 
  [./h]	
    type = SwitchingFunctionMaterial
    h_order = HIGH
    eta = eta
    outputs = exodus
  [../]
  [./h_phi]
    type = SwitchingFunctionMaterial
    function_name = h_phi
    h_order = HIGH
    eta = phi
    outputs = exodus
  [../]
  # g(eta)
  # [./g] 
  #   type = BarrierFunctionMaterial
  #   g_order = SIMPLE
  #   eta = eta
  # [../]
  [./multibarrier]
    type = MultiBarrierFunctionMaterial
    etas = 'eta phi'
    function_name = g
    outputs = exodus
  [../]
  [./crosstermbarrier_simple]
    type = CrossTermBarrierFunctionMaterial
    etas = 'eta phi'
    W_ij = '0   0.25
            0.25   0'
    function_name = gsimple
    g_order = SIMPLE
    outputs = exodus
  [../]
  # free energies
  [./free_energy_fs]
    type = DerivativeParsedMaterial
    property_name = fs
    coupled_variables = 'c eta phi'
    derivative_order = 2
    outputs = exodus  
    constant_names = 'As B_eta B_phi B_eta_phi'
    constant_expressions = '292 0.25 0.25 5.5'
    # constant_expressions = '218 0.25 0.25 5.5'
    material_property_names = 'length_scale energy_scale'
    expression = '
     (energy_scale/(length_scale)^3)*As*(c-0.4)^2
        
    '
  [../]
  [./free_energy_fl]
    type = DerivativeParsedMaterial
    property_name = fl
    coupled_variables = 'c eta phi '
    derivative_order = 2
    outputs = exodus
    constant_names = 'Al B_eta B_phi B_eta_phi'
    # constant_expressions = '454 0.25 0.25 3 '
    constant_expressions = '73 0.25 0.25 3 '
    material_property_names = 'length_scale energy_scale'
    expression = '
     (energy_scale/(length_scale)^3)*Al*(c-0.6)^2
        
    '
  [../]
  [./free_energy_chem]
    type = DerivativeTwoPhaseMaterial
    property_name = Fchem
    fa_name = fl
    fb_name = fs
    eta = eta
    coupled_variables = 'c phi'
    W = 2e3
    outputs = exodus
    derivative_order = 2
  [../] 
  [./free_energy_total]
    type = DerivativeSumMaterial
    property_name = F
    sum_materials = 'Fchem Fmech'
    coupled_variables = 'c eta phi'
    derivative_order = 2
    outputs = exodus
  [../]
  # BV driving force
  [./Butlervolmer]
    type = DerivativeParsedMaterial
    expression = 'L2*dh*(eta*exp(pot*(1-alpha)*Faraday*valency/RT)-c*exp(-pot*alpha*Faraday*valency/RT))'
    coupled_variables = 'pot c eta'
    property_name = f_bv
    material_property_names = 'L2 alpha Faraday valency RT dh:=D[h,eta]'
    outputs = exodus
    derivative_order = 1
  [../]
  [./monitor_BV1]
  	type = ParsedMaterial
    expression = 'eta*exp(pot*(1-alpha)*Faraday*valency/RT)'
    coupled_variables = 'pot eta'
    property_name = monitor_BV1
    material_property_names = 'alpha Faraday valency RT'
    outputs = exodus
  []  
  [./monitor_BV2]
  	type = ParsedMaterial
    expression = '-c*exp(-pot*alpha*Faraday*valency/RT)'
    coupled_variables = 'pot c'
    property_name = monitor_BV2
    material_property_names = 'alpha Faraday valency RT'
    outputs = exodus
  []  
  # diffusion for c
  [./Deff]
    type = ParsedMaterial
    expression = '(length_scale)^2/time_scale*(Meo*h+(h_phi*Mso+(1-h_phi)*Mlo)*(1-h))'
    # expression = '(length_scale)^2/time_scale*(Meo*h+Mlo*(1-h))' 
    property_name = Deff
    material_property_names = 'Meo Mso Mlo h_phi h length_scale time_scale'
    outputs = exodus
  [../]
  [./Deffe]
    type = DerivativeParsedMaterial
    expression = '(length_scale)^2/time_scale*(Meo*h+(h_phi*Mso+(1-h_phi)*Mlo)*(1-h))*c*valency*Faraday'
    # expression = '(length_scale)^2/time_scale*(Meo*h+Mso*(1-h))*c*valency*Faraday'
    coupled_variables = 'c'
    property_name = Deffe
    material_property_names = 'Meo Mso Mlo h_phi h length_scale time_scale valency Faraday'
    outputs = exodus
    derivative_order = 1
  [../]
  [./coupled_eta_function]
    type = ParsedMaterial
    expression = 'c_s/c_0'	# normalize
    property_name = ft
    material_property_names = 'c_s c_0'
    outputs = exodus
  [../]
  
  # Young's Modulus 
  [./E_eff]
    type = ParsedMaterial
    property_name = E_eff
    expression = 'h*Em + (1-h)*(h_phi*Ef + (1-h_phi)*Ee)'
    material_property_names = 'h h_phi Em Ee Ef'
    outputs = exodus
  [../]
  # mechical free energy
  [./elasticity_tensor]
    type = ComputeVariableIsotropicElasticityTensor
    youngs_modulus = E_eff
    poissons_ratio = nu_eff
    args = 'eta phi'
  [../]
  [./eigenstrain]
    type = ComputeVariableEigenstrain
    eigen_base = '-0.866e-3 0 0 0 -0.773e-3 0 0 0 -0.529e-3'
    prefactor = h
    args = 'eta'
    eigenstrain_name = eigenstrain
  [../]
  [./strain]
    type = ComputeSmallStrain
    displacements = 'disp_x disp_y'
    eigenstrain_names = eigenstrain
  [../]
  [./stress]
    type = ComputeLinearElasticStress
  [../]

  [./elastic_free_energy]
    type = ElasticEnergyMaterial
    property_name = Fmech
    coupled_variables = 'eta phi'
    derivative_order = 2
    outputs = exodus
  [../]

  # conduction for pot
  [./ElecEff]	
    type = ParsedMaterial
    # expression = '(h*S1o + (1-h)*S2o)/length_scale'
    expression = '(h*S1o + (1-h)*(h_phi*S3o + (1-h_phi)*S2o))/length_scale'
    property_name = ElecEff
    material_property_names = 'S1o S2o S3o h h_phi length_scale'
    outputs = exodus
  [../]
  [./ChargeEff]
    type = ParsedMaterial
    expression = 'valency*Faraday*c_s/(length_scale^3)'
    property_name = ChargeEff
    material_property_names = 'valency Faraday length_scale c_s'
    outputs = exodus
  [../]
  
[]

[Kernels]
  [./TensorMechanics]
  [../]
  
  #
  # Cahn-Hilliard Equation
  #
  [./dcdt]
    type = TimeDerivative
    variable = c
  [../]
  # Intrinsic diffusion part of equation 3 in main text.
  [./ch]
    type = CahnHilliard
    variable = c
    f_name = F
    mob_name = Deff
    coupled_variables = 'eta'
  [../]
  [./elec]
  	type = MatDiffusion
    variable = c
    v = pot
    diffusivity = Deffe
    args = 'eta c'
  [../]
  [./cSource] 
  	type = CoupledSusceptibilityTimeDerivative
    variable = c
    v = eta
    f_name = ft
  [../]
  
  # Allen-Cahn Equation   deta/dt
  #
  [./detadt]
    type = TimeDerivative
    variable = eta
  [../]
  [./ac]
    type = AllenCahn
    variable = eta
    coupled_variables = 'eta c'
  	f_name = F
  	mob_name = L1
  [../]
  [./ACInterface]
    type = ACInterface
    variable = eta
    kappa_name = kappa
    mob_name = L1
  [../]

 # Allen-Cahn Equation  dphi/dt
  [./dphidt]
    type = TimeDerivative
    variable = phi
  [../]
  [./ac_phi]
    type = AllenCahn
    variable = phi
    #coupled_variables = 'phi c'
  	f_name = F
  	mob_name = L1_phi
  [../]
  [./ACInterface_phi]
    type = ACInterface
    variable = phi
    kappa_name = kappa_phi
    mob_name = L1_phi
  [../]
    
  [./BV]
	type = MKinetics
	variable = eta
	f_name = f_bv
	coupled_variables = 'c pot eta'
  [../]
  [./noise_interface]
    type = LangevinNoise
    variable = eta
    #multiplier = mask_left*dh/deta
    multiplier = dh/deta
    amplitude = 1e-3
  [../]
  
  # evolution of pot ▽(σ▽φ)
  [./Cond]
    type = MatDiffusion
    variable = pot
    diffusivity = ElecEff
    args = 'eta'
  [../]
  # -nFcs(deta/dt)
  [./coupledSource]
    type = CoupledSusceptibilityTimeDerivative
    variable = pot
    v = eta
    f_name = ChargeEff
  [../]
[]

[AuxKernels]
  [./deta]
    type = DeltaUAux
    variable = delta_eta
    coupled_variable = eta   
    execute_on = timestep_end
  [../]
  [./dc]
    type = DeltaUAux
    variable = delta_c
    coupled_variable = c    
    execute_on = timestep_end
  [../]
  [./pot]
    type = DeltaUAux
    variable = delta_pot
    coupled_variable = pot    
    execute_on = timestep_end
  [../]
  [./grains_vis]
    type = ThreePhasesSumCdothsquare
    variable = gr_c
    var = phi
    h1 = eta
  [../]
  # [bnds]
  #   type                = BndsCalcAux
  #   variable            = 'bnds'
  #   var_name_base       = 'eta'
  #   op_num              = 2
  #   v                   = 'phi eta'
  # []
[]

[Executioner]
  type = Transient
  solve_type = 'NEWTON'
  
  petsc_options_iname = '-ksp_type -pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'preonly   lu        mumps'
  
  dtmax = 1E2
  end_time = 1E7
  
  [./TimeStepper]
    type = IterationAdaptiveDT
    dt = 1E-3
    growth_factor = 1.1
  [../]
  
  [./Adaptivity]
    interval = 5
    initial_adaptivity = 4
    refine_fraction = 0.8
    coarsen_fraction = 0.1
    max_h_level = 2
  [../]
[]

#
# Precondition using handcoded off-diagonal terms
#
[Preconditioning]
  [./full]
    type = SMP
    full = true
  [../]
[]

[Postprocessors]
  [./eta_min]
    type = NodalExtremeValue
    variable = eta
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./eta_max]
    type = NodalExtremeValue
    variable = eta
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./pot_min]
    type = NodalExtremeValue
    variable = pot
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./pot_max]
    type = NodalExtremeValue
    variable = pot
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
[]

[Outputs]
  exodus = true
  time_step_interval = 1
  file_base = results/solidmechdiff106/test1
[]

