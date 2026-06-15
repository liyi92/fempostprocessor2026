# Lily 2026/2/26

[GlobalParams]
  seed = 12345
[]

[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 50
  ny = 50
  xmin = 0
  xmax = 50
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
  [grad_eta_x]
    order   = FIRST
    family  = MONOMIAL
  []
  [grad_eta_y]
    order   = FIRST
    family  = MONOMIAL
  []
  [./grad_mag]
    order = CONSTANT
    family = MONOMIAL
  [../]
  [./eta_dot]
    order = CONSTANT
    family = MONOMIAL
  [../]
  [./J_at_x]
    order = CONSTANT
    family = MONOMIAL
  [../]
  [./J_at_y]
    order = CONSTANT
    family = MONOMIAL
  [../]
  [./J_at_mag]
    order = CONSTANT
    family = MONOMIAL
  [../]
[]

[ICs]
  [./eta]
    variable = eta
    type = FunctionIC
    #function = 'if(x>=0&x<=10,0.9,if(y<=30&y>=20,0.1,0.9))' #change the function
    function = 'if(x>=0&x<=10,0.99,0.01)'
  [../]
  [./phi]
    variable = phi
    type = FunctionIC
    function = 'if(x>=0&x<=10,0.01,if(y<=30&y>=20,0.01,0.99))'
    #function = 'if(x>=0&x<=5,0,if(y<=30&y>=20,0,0))' #phi=0 test
    #electrode(eta=0,phi=0)dendrite(eta=1,phi=0)inert(eta=0,phi=1)
  [../]
  [./c]
    variable = c	# lithium ion concentration
    type = FunctionIC
    function = 'if(x>=0&x<=10,0.2,if(y<=30&y>=20,0.4,0.5))'
    #function = '0.45'

  [../]
[]

[BCs]
  [./left_pot]
    type = DirichletBC
    variable = 'pot'
    boundary = 'left'
    value = -0.35
  [../]
  [./right_pot]
    type = DirichletBC
    variable = 'pot'
    boundary = 'right'
    value = 0
  [../]
  [./right_comp]	# connected to the electrolyte
   type = DirichletBC
   variable = c
   boundary = right
   value = 0.5
  [../] 
  # [./right_eta]	# connected to the electrolyte
  #   type = NeumannBC
  #   variable = 'eta'
  #   boundary = 'right'
  # [../]
[]
[Materials]
  [./scale]
    type = GenericConstantMaterial
    prop_names = 'length_scale energy_scale time_scale'#um,ev,ms
    prop_values = '1e6 6.24150943e18 1e3'
  [../]
  [./constants]
    type = GenericConstantMaterial
    prop_names  = 'c_s c_0 valency molar_vol Faraday RT alpha'
    #prop_values = '7.64e4 1e3 1 2.2e-5 96485 2494.2 0.5'
    prop_values = '7e4 1e3 1 2.2e-5 96485 2494.2 0.5'
  [../]
  [./system_constants]
    type = GenericConstantMaterial
    prop_names  = 'L1o L1o_phi L2o ko ko_phi S1o S2o'
    # prop_values = '5.6e2 0.025 1.39e-4 0.7e-10 0.7e-11 1e7 1'
    #prop_values = '75 0.01 1e-3 1.65e-9 1.655e-10  1e7 1'
    prop_values = '25 0.01 0.1 2.5e-11 2.5e-12 1e7 1'
    #prop_values = '5.6e2 0.025 1.39e-4 1.65e-9 1.655e-10  1e7 1' 
  [../]
  [./system_constants2]
    type = GenericConstantMaterial
    prop_names  = 'Meo Mso'
    #prop_values = '1.8e-15 2.3e-15'
    prop_values = '1e-13 5e-13'
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
  [./h_eta]
    type = SwitchingFunctionMaterial
    h_order = HIGH
    eta = eta
    outputs = exodus
  [../]

  [./dh_eta_deta_mat]
    type = DerivativeParsedMaterial
    property_name = dh_eta_deta_mat
    coupled_variables = 'eta'
    material_property_names = 'dh_eta_deta:=D[h_eta,eta]'
    expression = 'dh_eta_deta'
    derivative_order = 1
    outputs = exodus
  [../]
  #g(eta)
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
  [./free_energy_fs]
    type = DerivativeParsedMaterial
    property_name = fs
    coupled_variables = 'c'
    derivative_order = 2
    outputs = exodus
    material_property_names =  'length_scale energy_scale'
    constant_names = 'As B_etas B_phis B_eta_phis'
    constant_expressions = '3 0.25 0.2 5.5'
    #expression = '(energy_scale/(length_scale)^3)*As*(c-0.5)^2+B_etas*eta^2*(1-eta)^2 + B_phis*phi^2*(1-phi)^2+ B_eta_phis*eta^2*phi^2 '
    expression = ' 
    As*(c-0.2)^2
    '
  [../]
  [./free_energy_fl]
    type = DerivativeParsedMaterial
    property_name = fl
    coupled_variables = 'c'
    derivative_order = 2
    outputs = exodus
    material_property_names =  'length_scale energy_scale'
    constant_names = 'Al B_eta B_phi B_eta_phi'
    constant_expressions = '1 0.25 0.2 3'
    #expression = '(energy_scale/(length_scale)^3)*Al*(c-0.2)^2+B_eta*eta^2*(1-eta)^2 + B_phi*phi^2*(1-phi)^2+ B_eta_phi*eta^2*phi^2'
    expression = '
      Al*(c-0.5)^2
    '
  [../]
  [./free_energy]
    type = DerivativeTwoPhaseMaterial
    property_name = F
    fa_name = fl
    fb_name = fs
    eta = eta
    coupled_variables = 'c phi'
    # coupled_variables = 'c '
    W = 30
    #W = 6.24
    outputs = exodus
    derivative_order = 2
  [../] 
  
  # BV driving force
  [./Butlervolmer]
    type = DerivativeParsedMaterial
    expression = 'L2*dh_eta_deta_mat*(eta*exp(pot*(1-alpha)*Faraday*valency/RT)-c*exp(-pot*alpha*Faraday*valency/RT))'
    coupled_variables = 'pot c eta'
    property_name = f_bv
    material_property_names = 'L2 alpha Faraday valency RT dh_eta_deta_mat'
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
    expression = '(length_scale)^2/time_scale*(Meo*h_eta+Mso*(1-h_eta))'
    property_name = Deff
    material_property_names = 'Meo Mso h_eta length_scale time_scale'
    outputs = exodus
  [../]
  [./Deffe]
    type = DerivativeParsedMaterial
    expression = '(length_scale)^2/time_scale*(Meo*h_eta+Mso*(1-h_eta))*c*valency*Faraday/RT'
    coupled_variables = 'c'
    property_name = Deffe
    material_property_names = 'Meo Mso h_eta length_scale time_scale valency Faraday RT'
    outputs = exodus
    derivative_order = 1
  [../]
  [./partition_coeff]
    type = GenericConstantMaterial
    prop_names = 'c_s_eq c_l_eq a_at W_at eps_grad'
    prop_values = '0.2 0.5 0.707 5 1e-6'
  [../]
  [./J_at_x_material]
   type = ParsedMaterial
   property_name = J_at_x_mat
   coupled_variables = 'grad_eta_x grad_eta_y eta_dot'
   material_property_names = 'a_at W_at c_l_eq c_s_eq eps_grad'
   expression = '-a_at*W_at*(c_l_eq-c_s_eq)*eta_dot*grad_eta_x/sqrt(grad_eta_x^2+grad_eta_y^2+eps_grad)'
   outputs = exodus
  [../]

  [./J_at_y_material]
   type = ParsedMaterial
   property_name = J_at_y_mat
   coupled_variables = 'grad_eta_x grad_eta_y eta_dot'
   material_property_names = 'a_at W_at c_l_eq c_s_eq eps_grad'
   expression = '-a_at*W_at*(c_l_eq-c_s_eq)*eta_dot*grad_eta_y/sqrt(grad_eta_x^2+grad_eta_y^2+eps_grad)'
   outputs = exodus
  [../]

  [./J_at_mag_material]
   type = ParsedMaterial
   property_name = J_at_mag_mat
   coupled_variables = 'J_at_x J_at_y'
   expression = 'sqrt(J_at_x^2+J_at_y^2)'
   outputs = exodus
  [../]
  
  [./source_coefficient]
    type = ParsedMaterial
    expression = 'dh_eta_deta_mat*(c_s_eq-c_l_eq)'
    property_name = source_coeff
    material_property_names = 'dh_eta_deta_mat c_s_eq c_l_eq'
    outputs = exodus
  [../]
  # conduction for pot
  [./ElecEff]	
    type = ParsedMaterial
    expression = '(S1o*h_eta+S2o*(1-h_eta))/length_scale'
    property_name = ElecEff
    material_property_names = 'S1o S2o h_eta length_scale'
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
  # Cahn-Hilliard Equation
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
    #coupled_variables = 'eta phi'
    coupled_variables = 'eta'
  [../]
  [./elec]
  	type = MatDiffusion
    variable = c
    v = pot
    diffusivity = Deffe
    args = 'eta c'
  [../]

  [./Interface_Source] 
    type = CoupledSusceptibilityTimeDerivative
    variable = c
    v = eta
    f_name = source_coeff
  [../]
  [./atc_flux]
    type = CoupledSusceptibilityTimeDerivative
    variable = c
    v = eta
    f_name = J_at_mag_mat
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
    #coupled_variables = 'eta phi c'
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
    coupled_variables = 'eta c'
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
    multiplier = dh_eta_deta_mat
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
  # [./grains_vis]
  #   type = ThreePhasesSumCdothsquare
  #   variable = gr_c
  #   var = phi
  #   h1 = eta
  # [../]
  # [bnds]
  #   type                = BndsCalcAux
  #   variable            = 'bnds'
  #   var_name_base       = 'eta'
  #   op_num              = 2
  #   v                   = 'phi eta'
  # []
  [grad_eta_x]
    type              = VariableGradientComponent
    variable          = 'grad_eta_x'
    gradient_variable = 'eta'
    component         = 'x'
    execute_on        = 'LINEAR'
  []
  [grad_eta_y]
    type              = VariableGradientComponent
    variable          = 'grad_eta_y'
    gradient_variable = 'eta'
    component         = 'y'
    execute_on        = 'LINEAR'
  []

  [./eta_dot_aux]
    type = TimeDerivativeAux
    variable = eta_dot
    functor = 'eta'
    execute_on = 'TIMESTEP_END'
  [../]

  [./J_at_x_aux]
    type = MaterialRealAux
    variable = J_at_x
    property = J_at_x_mat
    execute_on = 'TIMESTEP_END'
  [../]
  [./J_at_y_aux]
    type = MaterialRealAux
    variable = J_at_y
    property = J_at_y_mat
    execute_on = 'TIMESTEP_END'
  [../]
  [./J_at_mag_aux]
    type = MaterialRealAux
    variable = J_at_mag
    property = J_at_mag_mat
    execute_on = 'TIMESTEP_END'
  [../]
[]

[Executioner]
  type = Transient
  solve_type = 'NEWTON'
  
  petsc_options_iname = '-ksp_type -pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'preonly   lu        mumps'
  
  dtmax = 1E1
  end_time = 1E7
  
  nl_rel_tol = 1e-6
  nl_abs_tol = 1e-8
  nl_max_its = 30
  l_tol = 1e-4
  l_max_its = 100
  
  [./TimeStepper]
    type = IterationAdaptiveDT
    dt = 1E-6
    #growth_factor = 1.1
    growth_factor = 1.02
  [../]
  
  [./Adaptivity]
    interval = 5
    initial_adaptivity = 4
    #refine_fraction = 0.8
    refine_fraction = 0.6
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
  file_base = results/solidtwokksgradACCHISpotnoifluxphi15/test1
[]

