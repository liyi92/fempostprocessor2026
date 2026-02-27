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
[]

[ICs]
  [./eta]
    variable = eta
    type = FunctionIC
    function = 'if(x>=0&x<=5,0,if(y<=30&y>=20,1,0))' #change the function
  [../]
  [./phi]
    variable = phi
    type = FunctionIC
    function = 'if(x>=0&x<=5,0,if(y<=30&y>=20,0,1))'
    #electrode(eta=0,phi=0)dendrite(eta=1,phi=0)inert(eta=0,phi=1)
  [../]
  [./c]
    variable = c	# lithium ion concentration
    type = FunctionIC
    function = 'if(x>=0&x<=5,0.2,0.5)'
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
    prop_values = '7.69e4 1e3 1 2.2e-5 96485 2494.2 0.5'
  [../]
  [./system_constants]
    type = GenericConstantMaterial
    prop_names  = 'Meo Mso M L1o L1o_phi L2o ko ko_phi S1o S2o'
    prop_values = '1e-13 5e-13 1e-8 0.25 0.25 0.1 1e-11 1e-11 1e7 1.19'
  [../]
  [./material_constants]
    type = GenericConstantMaterial
    prop_names  = 'fo Al As Bl Bs Cl Cs cleq cseq'	# j/mol
    prop_values = '0.01 1 3 2 1.5 0 0 0.6 0.4'
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
  # g(eta)
  [./g] 
    type = BarrierFunctionMaterial
    g_order = SIMPLE
    eta = eta
  [../]
  # [./g_phi] 
  #   type = BarrierFunctionMaterial
  #   g_order = SIMPLE
  #   eta = phi
  # [../]
  # free energies
  # [./fl]
  #   type = DerivativeParsedMaterial
  #   property_name = fl
  #   material_property_names = 'fo Al Bl Cl cleq length_scale energy_scale molar_vol'
  #   coupled_variables = 'c'
  #   expression = '(energy_scale/(length_scale)^3)*(Al*(c-cleq)^2 + Bl*(c-cleq) + Cl)*fo/molar_vol'
  #   #expression = '(energy_scale/(length_scale)^3)*(Al*(1-c)^2 + Bl*(c-cleq) + Cl)*fo/molar_vol'
  #   outputs = exodus
  #   derivative_order = 2
  # [../]
  # [./fs]
  #   type = DerivativeParsedMaterial
  #   property_name = fs
  #   material_property_names = 'fo As Bs Cs cseq length_scale energy_scale molar_vol'
  #   coupled_variables = 'c'
  #   expression = '(energy_scale/(length_scale)^3)*(As*(c-cseq)^2 + Bs*(c-cseq) + Cs)*fo/molar_vol'
  #   outputs = exodus
  #   derivative_order = 2
  # [../]
  # [./free_energy]
  #   type = DerivativeTwoPhaseMaterial
  #   property_name = F
  #   fa_name = fl
  #   fb_name = fs
  #   eta = eta
  #   coupled_variables = 'c'
  #   W = 2e3
  #   outputs = exodus
  #   derivative_order = 2
  # [../]  
    [./free_energy]
    type = DerivativeParsedMaterial
    property_name = F
    coupled_variables = 'c eta phi'
    derivative_order = 2
    outputs = exodus
    constant_names = 'A B'
    constant_expressions = '1.0 2e3'

    expression = '
      A*c^2*(1-c)^2
      +
      B*(
          c^2
          + 6*(1-c)*( eta^2 + phi^2 + (1-eta-phi)^2 )
          - 4*(2-c)*( eta^3 + phi^3 + (1-eta-phi)^3 )
          + 3*( eta^2 + phi^2 + (1-eta-phi)^2 )^2
        )
    '
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
    expression = '(length_scale)^2/time_scale*(Meo*h+Mso*(1-h))'
    property_name = Deff
    material_property_names = 'Meo Mso h length_scale time_scale'
    outputs = exodus
  [../]
  [./Deffe]
    type = DerivativeParsedMaterial
    expression = '(length_scale)^2/time_scale*(Meo*h+Mso*(1-h))*c*valency*Faraday'
    coupled_variables = 'c'
    property_name = Deffe
    material_property_names = 'Meo Mso h length_scale time_scale valency Faraday'
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
  # conduction for pot
  [./ElecEff]	
    type = ParsedMaterial
    expression = '(S1o*h+S2o*(1-h))/length_scale'
    property_name = ElecEff
    material_property_names = 'S1o S2o h length_scale'
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
    #coupled_variables = 'phi'
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
  file_base = results/LiSinglev33/LiSingle
[]

