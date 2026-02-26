#KKS model 4eta BV 
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
  [./eta1]
    order = FIRST
    family = LAGRANGE
  [../]

  [./eta2]
    order = FIRST
    family = LAGRANGE
  [../]

  [./eta3]
    order = FIRST
    family = LAGRANGE
  [../]

  [./eta4]
    order = FIRST
    family = LAGRANGE
  [../]

  # solute concentration
  [./c]
    order = FIRST
    family = LAGRANGE
  [../]

  [./c1]
    order = FIRST
    family = LAGRANGE
  [../]

  [./c2]
    order = FIRST
    family = LAGRANGE
  [../]

  [./c3]
    order = FIRST
    family = LAGRANGE
  [../]

  [./c4]
    order = FIRST
    family = LAGRANGE
  [../]
  # [w]
  #   order = FIRST
  #   family = LAGRANGE
  # []
  # # electric overpotential
  # [./pot]
  #   order = FIRST
  #   family = LAGRANGE
  # [../]

[]

[AuxVariables]
  [./bnds]
  [../]
  [./delta_eta1]
  [../]
  [./delta_eta2]
  [../]
  [./delta_c1]
  [../]
  [./delta_c2]
  [../]     
  [./delta_eta3]
  [../]
  [./delta_c3]
  [../]
  [./delta_eta4]
  [../]
  [./delta_c4]
  [../]
  [./delta_eta]
  [../]
  [./delta_c]
  [../]
  [./delta_pot]
  [../]
  [c_mix]
  []
  [eta_sum]
  []
  [Fglobal]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[ICs]
  [./eta1]
    variable = eta1
    type = FunctionIC
    function = 'if(x<=5,0.99,0.01)'
  [../]

  [./eta2]
    variable = eta2
    type = FunctionIC
    function = 'if(y<=20&x>5,0.99,0.01)'
  [../]

  [./eta3]
    variable = eta3
    type = FunctionIC
    function = 'if(y>=30&x>5,0.99,0.01)'
  [../]

  [./eta4]
    variable = eta4
    type = FunctionIC
    function = 'if(x>5&y>20&y<30,0.99,0.01)'
  [../]


  [./c1]
    variable = c1	# lithium ion concentration
    type = FunctionIC
    function = 'if(x<=5,0.2,0.0001)'
  [../]

  [./c2]
    variable = c2	
    type = FunctionIC
    function = 'if(y<=20&x>5,0.5,0.0001)'
  [../]

  [./c3]
    variable = c3	
    type = FunctionIC
    function = 'if(y>=30&x>5,0.5,0.0001)'
  [../]

  [./c4]
    variable = c4	
    type = FunctionIC
    function = 'if(y>20&y<30&x>5,0.1,0.0001)'
  [../] 
  [./c]
    variable = c
    type = FunctionIC
    function = '
      if(x<=5,0.2,
      if(y<=20&x>5,0.5,
      if(y>=30&x>5,0.5,
      if(y>20&y<30&x>5,0.3,0.5))))'
  [../]
  # [./pot_ic]
  #   type = FunctionIC
  #   variable = pot
  #   function = '-0.35 + (0.001+0.35)*x/50'
  # [../]
[]
[BCs]
  # [./left_pot]
  #   type = DirichletBC
  #   variable = 'pot'
  #   boundary = 'left'
  #   value = -0.35
  # [../]
  # [./right_pot]
  #   type = DirichletBC
  #   variable = 'pot'
  #   boundary = 'right'
  #   value = 0.001
  # [../]
  [right_c]
    type = DirichletBC
    variable = c
    boundary = right
    value = 0.5
  []

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
    prop_names = 'M1 M2 M3 M4 L1o L2o ko S1 S2 gamma mu'
    prop_values = '1e-12 1e-15 1e-15 5e-12 5.6e-4 2.5 1e-11 1e7 1.19 1 1'
  [../]
  [./material_constants]
    type = GenericConstantMaterial
    prop_names  = 'fo A1 A2 A3 A4 B1 B2 B3 B4 C1 C2 C3 C4 c1eq c2eq c3eq c4eq'	# j/mol
    #prop_values = '0.01 1.2 0.7 0.7 0.3   -2.5 4.5 4.5 3   -7 5.6 5.6 10   0.2 0.5 0.5 0.1'
    prop_values = '0.01 1 0.7 0.7 0.3   -2.5 4.5 4.5 3   -7 5.6 5.6 10   0.2 0.5 0.5 0.1'
  [../]
  [./L1]
    type = ParsedMaterial
    expression = '((length_scale)^3/(energy_scale*time_scale))*L1o'
    property_name = L1
    material_property_names = 'L1o length_scale energy_scale time_scale'
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
  # h(eta) 
  [./h1]	
    type = SwitchingFunctionMultiPhaseMaterial
    h_name = h1
    all_etas = 'eta1 eta2 eta3 eta4'
    phase_etas = eta1
  [../]
  [./h2]	
    type = SwitchingFunctionMultiPhaseMaterial
    h_name = h2
    all_etas = 'eta1 eta2 eta3 eta4'
    phase_etas = eta2
  [../]
  [./h3]	
    type = SwitchingFunctionMultiPhaseMaterial
    h_name = h3
    all_etas = 'eta1 eta2 eta3 eta4'
    phase_etas = eta3
  [../]
  [./h4]	
    type = SwitchingFunctionMultiPhaseMaterial
    h_name = h4
    all_etas = 'eta1 eta2 eta3 eta4'
    phase_etas = eta4
  [../]
  # g(eta)
  [./g1] 
    type = BarrierFunctionMaterial
    g_order = SIMPLE
    eta = eta1
    function_name = g1
  [../]

  [./g2] 
    type = BarrierFunctionMaterial
    g_order = SIMPLE
    eta = eta2
    function_name = g2
  [../]

  [./g3] 
    type = BarrierFunctionMaterial
    g_order = SIMPLE
    eta = eta3
    function_name = g3
  [../]

  [./g4] 
    type = BarrierFunctionMaterial
    g_order = SIMPLE
    eta = eta4
    function_name = g4
  [../]

  # [mu]
  #       type = ParsedMaterial
  #       f_name = mu
  #       prop_names  = 'sigma delta '
  #       prop_values = '1 1'
  #       material_property_names = 'sigma delta energy_scale length_scale'
  #       function = '6*(sigma/delta)*(energy_scale/length_scale^3)' 
  # []

  # free energies 
  [./f1]
    type = DerivativeParsedMaterial
    property_name = f1
    #material_property_names = 'fo A1 B1 C1 c1eq length_scale energy_scale molar_vol'
    material_property_names = 'length_scale energy_scale molar_vol'
    coupled_variables = 'c1'
    #expression = '(energy_scale/(length_scale)^3)*(A1*(c1-c1eq)^2 + B1*(c1-c1eq) + C1)*fo/molar_vol'
    expression = '(energy_scale/(length_scale)^3)*((c1-2)^2 +0.9326)'
    outputs = exodus
    derivative_order = 2
  [../]
  [./f2]
    type = DerivativeParsedMaterial
    property_name = f2
    #material_property_names = 'fo A2 B2 C2 c2eq length_scale energy_scale molar_vol'
    material_property_names = 'length_scale energy_scale molar_vol'
    coupled_variables = 'c2'
    #expression = '(energy_scale/(length_scale)^3)*(A2*(c2-c2eq)^2 + B2*(c2-c2eq) + C2)*fo/molar_vol'
    expression = '(energy_scale/(length_scale)^3)*(3.7*(c2-2)^2 +0.9326)'
    outputs = exodus
    derivative_order = 2
  [../]
  [./f3]
    type = DerivativeParsedMaterial
    property_name = f3
    #material_property_names = 'fo A3 B3 C3 c3eq length_scale energy_scale molar_vol'
    material_property_names = 'length_scale energy_scale molar_vol'
    coupled_variables = 'c3'
   # expression = '(energy_scale/(length_scale)^3)*(A3*(c3-c3eq)^2 + B3*(c3-c3eq) + C3)*fo/molar_vol'
    expression = '(energy_scale/(length_scale)^3)*(3.7*(c3-2)^2 +0.9326)'
    outputs = exodus
    derivative_order = 2
  [../]
  [./f4]
    type = DerivativeParsedMaterial
    property_name = f4
    #material_property_names = 'fo A4 B4 C4 c4eq length_scale energy_scale molar_vol'
    material_property_names = 'length_scale energy_scale molar_vol'
    coupled_variables = 'c4'
    #expression ='energy_scale / (length_scale * length_scale * length_scale) * (A4 * (c4 - c4eq) * (c4 - c4eq) + B4 * (c4 - c4eq) + C4) * fo / molar_vol'
    expression = '(energy_scale/(length_scale)^3)*((c4-3)^2*(c4-1)^2+0.25*(c4-1)^2)'
    outputs = exodus
    derivative_order = 2
  [../]
 # 合成一个给 DerivativeMultiPhaseMaterial 用的 barrier：g = w1*g1 + w2*g2 + w3*g3 + w4*g4
  [./g_sum]
    type = DerivativeSumMaterial
    property_name = g
    sum_materials = 'g1 g2 g3 g4'
    prefactor = '1 1 1 1'              
    coupled_variables = 'eta1 eta2 eta3 eta4'
    derivative_order = 2
    outputs = exodus
  [../]


  [./free_energy]
    type = DerivativeMultiPhaseMaterial
    property_name = F
    fi_names = 'f1 f2 f3 f4'
    hi_names = 'h1 h2 h3 h4'
    g=g
    etas     = 'eta1 eta2 eta3 eta4'
    coupled_variables = 'c1 c2 c3 c4'
    W = 1e3
    outputs = exodus
    derivative_order = 2
  [../]
    
  # # BV driving force
  # [./Butlervolmer]
  #   type = DerivativeParsedMaterial
  #   expression = 'L2*dh*( eta4*exp( max(-50,min(50, pot*(1-alpha)*Faraday*valency/RT)))- max(c4,1e-12)*exp(max(-50,min(50, -pot*alpha*Faraday*valency/RT))))'
  #   coupled_variables = 'pot c4 eta4'
  #   property_name = f_bv
  #   material_property_names = 'L2 alpha Faraday valency RT dh:=D[h4,eta4]'
  #   outputs = exodus
  #   derivative_order = 1
  # [../]
#   [./monitor_BV1]
#   	type = ParsedMaterial
#     expression = 'eta4*exp(pot*(1-alpha)*Faraday*valency/RT)'
#     coupled_variables = 'pot eta4'
#     property_name = monitor_BV1
#     material_property_names = 'alpha Faraday valency RT'
#     outputs = exodus
#   [../]  
#   [./monitor_BV2]
#   	type = ParsedMaterial
#     expression = '-c4*exp(-pot*alpha*Faraday*valency/RT)'
#     coupled_variables = 'pot c4'
#     property_name = monitor_BV2
#     material_property_names = 'alpha Faraday valency RT'
#     outputs = exodus
#   [../]  
  #diffusion for c
  [./Deff]
    type = ParsedMaterial
    expression = '(length_scale)^2/time_scale*(M1*h1 + M2*h2 + M3*h3 + M4*h4)'
    material_property_names = 'M1 M2 M3 M4 h1 h2 h3 h4 length_scale time_scale'
    property_name = Deff
    outputs = exodus
  [../]
  [./Deffe]
    type = DerivativeParsedMaterial
    expression = '(length_scale)^2/time_scale*(M4*h4)*c*valency*Faraday'
    coupled_variables = 'c'
    property_name = Deffe
    material_property_names = 'M4 h4 length_scale time_scale valency Faraday'
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
  # [./ElecEff]	
  #   type = ParsedMaterial
  #   expression = '(S1*h1+S2*h4)/length_scale'
  #   property_name = ElecEff
  #   material_property_names = 'S1 S2 h1 h4 length_scale'
  #   outputs = exodus
  # [../]
  # [./ChargeEff]
  #   type = ParsedMaterial
  #   expression = 'valency*Faraday*c_s/(length_scale^3)'
  #   property_name = ChargeEff
  #   material_property_names = 'valency Faraday length_scale c_s'
  #   outputs = exodus
  # [../]
  # [./M_alias]
  #   type = ParsedMaterial
  #   property_name = M
  #   expression = 'Deff'
  #   material_property_names = 'Deff'
  # [../]

  # [./h_alias]
  #   type = ParsedMaterial
  #   property_name = h
  #   expression = 'h4'
  #   material_property_names = 'h4'
  # [../]
[]

[Kernels]
 # KKS Constraints
    [chempot14]
        type = KKSPhaseChemicalPotential
        variable = c1
        cb = c4
        fa_name = f1
        fb_name = f4
        args_a = 'eta1 eta2 eta3 eta4 c2 c3'
        args_b = 'eta1 eta2 eta3 eta4 c2 c3'
    []
     [chempot24]
        type = KKSPhaseChemicalPotential
        variable = c2
        cb = c4
        fa_name = f2
        fb_name = f4
        args_a = 'eta1 eta2 eta3 eta4 c1 c3'
        args_b = 'eta1 eta2 eta3 eta4 c1 c3'
    []
     [chempot34]
        type = KKSPhaseChemicalPotential
        variable = c3
        cb = c4
        fa_name = f3
        fb_name = f4
        args_a = 'eta1 eta2 eta3 eta4 c2 c1'
        args_b = 'eta1 eta2 eta3 eta4 c2 c1'
    []

    [phaseconcentration]
        type = KKSMultiPhaseConcentration
        variable = c4
        cj = 'c1 c2 c3 c4'
        hj_names = 'h1 h2 h3 h4'
        etas = 'eta1 eta2 eta3 eta4'
        c = c
    []

 # Cahn-Hilliard Equation
  [./dcdt]
    type = TimeDerivative
    variable = c
  [../]


  # [./dcdt1]
  #   type = TimeDerivative
  #   variable = c1
  # [../]  
  # [./dcdt2]
  #   type = TimeDerivative
  #   variable = c2
  # [../]
  # [./dcdt3]
  #   type = TimeDerivative
  #   variable = c3
  # [../]
  # [./dcd4]
  #   type = TimeDerivative
  #   variable = c4
  # [../]
  # [ckernel] 
  #   type                    = SplitCHWRes
  #   mob_name                = Deff
  #   variable                = 'w'
  #   coupled_variables       = 'eta1 eta2 eta3 eta4'
  # []
  # [CHBulk] # Gives the residual for the concentration, dF/dcA-mu 化学势相等
  #   type                    = KKSSplitCHCRes   
  #   variable                = 'c'
  #   ca                      = 'c4'
  #   fa_name                 = 'f1'
  #   w                       = 'w'
  #   args_a                  = 'c1'
  #   []
  # [chkernel] # Gives residual for chemical potential dc/dt+M\grad(mu)
  #     type = CahnHilliard
  #     mob_name = Deff
  #     variable = c
  #     f_name = F
  #     coupled_variables = 'c1 c2 c3 c4 eta1 eta2 eta3 eta4'
  # []   
 
#   #∇⋅(Deff(e)​∇ϕ)
#   [./elec]
#   	type = MatDiffusion
#     variable = c
#     v = pot
#     diffusivity = Deffe
#     args = 'eta4'
#   [../]

#  #deta/dt
#   [./cSource] 
#   	type = CoupledSusceptibilityTimeDerivative
#     variable = c
#     v = 'eta4'
#     f_name = ft
#   [../]

  # Allen-Cahn Equation eta1 
  #
  [./detadt1]
    type = TimeDerivative
    variable = eta1
  [../]
   [ACBulkF1]
        type = KKSMultiACBulkF
        variable = eta1
        Fj_names = 'f1 f2 f3 f4'
        hj_names = 'h1 h2 h3 h4'
        gi_name = g1
        eta_i = eta1
        wi = 1e3
        coupled_variables = 'c1 c2 c3 c4 eta2 eta3 eta4'
        mob_name = L1
    []

    [ACBulkC1]
        type = KKSMultiACBulkC
        variable = eta1
        Fj_names = 'f1 f2 f3 f4'
        hj_names = 'h1 h2 h3 h4'
        cj_names = 'c1 c2 c3 c4'
        eta_i = eta1
        coupled_variables = 'eta2 eta3 eta4'
        mob_name = L1
    []
  [./ACInterface1]
    type = ACInterface
    variable = eta1
    kappa_name = kappa
    mob_name = L1
  [../]
  [ACdfintdeta1] #L*m*(eta_i^3-eta_i+2*beta*eta_i*sum_j eta_j^2)
        type = ACGrGrMulti
        variable = eta1
        gamma_names = 'gamma gamma gamma'
        mob_name = L1
        v = 'eta2 eta3 eta4'
  []

  # Allen-Cahn Equation eta2 
  #
  [./detadt2]
    type = TimeDerivative
    variable = eta2
  [../]
   [ACBulkF2]
      type = KKSMultiACBulkF
      variable = eta2
      Fj_names = 'f1 f2 f3 f4'
      hj_names = 'h1 h2 h3 h4'
      gi_name = g2
      eta_i = eta2
      wi = 1e3
      coupled_variables = 'c1 c2 c3 c4 eta1 eta3 eta4'
      mob_name = L1
   []

    [ACBulkC2]
      type = KKSMultiACBulkC
      variable = eta2
      Fj_names = 'f1 f2 f3 f4'
      hj_names = 'h1 h2 h3 h4'
      cj_names = 'c1 c2 c3 c4'
      eta_i = eta2
      coupled_variables = 'eta1 eta3 eta4'
      mob_name = L1
    []
  [./ACInterface2]
    type = ACInterface
    variable = eta2
    kappa_name = kappa
    mob_name = L1
  [../]
  [ACdfintdeta2] #L*m*(eta_i^3-eta_i+2*beta*eta_i*sum_j eta_j^2)
        type = ACGrGrMulti
        variable = eta2
        gamma_names = 'gamma gamma gamma'
        mob_name = L1
        v = 'eta1 eta3 eta4'
  []

  # Allen-Cahn Equation eta3 
  #
  [./detadt3]
    type = TimeDerivative
    variable = eta3
  [../]
     [ACBulkF3]
        type = KKSMultiACBulkF
        variable = eta3
        Fj_names = 'f1 f2 f3 f4'
        hj_names = 'h1 h2 h3 h4'
        gi_name = g3
        eta_i = eta3
        wi = 1e3
        coupled_variables = 'c1 c2 c3 c4 eta2 eta1 eta4'
        mob_name = L1
    []

    [ACBulkC3]
        type = KKSMultiACBulkC
        variable = eta3
        Fj_names = 'f1 f2 f3 f4'
        hj_names = 'h1 h2 h3 h4'
        cj_names = 'c1 c2 c3 c4'
        eta_i = eta3
        coupled_variables = 'eta2 eta1 eta4'
        mob_name = L1
    []
  [./ACInterface3]
    type = ACInterface
    variable = eta3
    kappa_name = kappa
    mob_name = L1
  [../]
  [ACdfintdeta3] #L*m*(eta_i^3-eta_i+2*beta*eta_i*sum_j eta_j^2)
        type = ACGrGrMulti
        variable = eta3
        gamma_names = 'gamma gamma gamma'
        mob_name = L1
        v = 'eta2 eta1 eta4'
  []


  # Allen-Cahn Equation eta4 
  #
  [./detadt4]
    type = TimeDerivative
    variable = eta4
  [../]
   [ACBulkF4]
        type = KKSMultiACBulkF
        variable = eta4
        Fj_names = 'f1 f2 f3 f4'
        hj_names = 'h1 h2 h3 h4'
        gi_name = g4
        eta_i = eta4
        wi = 1e3
        coupled_variables = 'c1 c2 c3 c4 eta2 eta3 eta1'
        mob_name = L1
    []

    [ACBulkC4]
        type = KKSMultiACBulkC
        variable = eta4
        Fj_names = 'f1 f2 f3 f4'
        hj_names = 'h1 h2 h3 h4'
        cj_names = 'c1 c2 c3 c4'
        eta_i = eta4
        coupled_variables = 'eta2 eta3 eta1'
        mob_name = L1
    []
  [./ACInterface4]
    type = ACInterface
    variable = eta4
    kappa_name = kappa
    mob_name = L1
  [../]
  [ACdfintdeta4] #L*m*(eta_i^3-eta_i+2*beta*eta_i*sum_j eta_j^2)
        type = ACGrGrMulti
        variable = eta4
        gamma_names = 'gamma gamma gamma'
        mob_name = L1
        v = 'eta2 eta3 eta1'
  []



  # [./BV]
	#  type = MKinetics
	#  variable = eta4
	#  f_name = f_bv
	#  coupled_variables = 'c4 pot eta4'
  # [../]
  # [./noise_interface]
  #   type = LangevinNoise
  #   variable = eta4
  #   multiplier = h4
  #   amplitude = 1e-4
  # [../]
  
  # # evolution of pot ▽(σ▽φ)
  # [./Cond]
  #   type = MatDiffusion
  #   variable = pot
  #   diffusivity = ElecEff
  #   #args = 'eta4'
  # [../]
  # # -nFcs(deta/dt)
  # [./coupledSource]
  #   type = CoupledSusceptibilityTimeDerivative
  #   variable = pot
  #   v = eta4
  #   f_name = ChargeEff
  # [../]
[]

[AuxKernels]
[./bnds]
    type = BndsCalcAux
    variable = bnds
    var_name_base = eta
    op_num = 4 #2
    v = 'eta1 eta2 eta3 eta4' #Not writing a variable here will put a 0 value on the eta value of the absentee
  [../]


[./deta1]
    type = DeltaUAux
    variable = delta_eta1
    coupled_variable = eta1  
    execute_on = timestep_end
  [../]
  [./deta2]
    type = DeltaUAux
    variable = delta_eta2
    coupled_variable = eta2   
    execute_on = timestep_end
  [../]
  [./deta3]
    type = DeltaUAux
    variable = delta_eta3
    coupled_variable = eta3  
    execute_on = timestep_end
  [../]
  [./deta4]
    type = DeltaUAux
    variable = delta_eta4
    coupled_variable = eta4   
    execute_on = timestep_end
  [../]
  # [./deta]
  #   type = DeltaUAux
  #   variable = delta_eta
  #   coupled_variable = eta   
  #   execute_on = timestep_end
  # [../]

  # [./dc1]
  #   type = DeltaUAux
  #   variable = delta_c1
  #   coupled_variable = c1    
  #   execute_on = timestep_end
  # [../]
  # [./dc2]
  #   type = DeltaUAux
  #   variable = delta_c2
  #   coupled_variable = c2    
  #   execute_on = timestep_end
  # [../]
  # [./dc3]
  #   type = DeltaUAux
  #   variable = delta_c3
  #   coupled_variable = c3   
  #   execute_on = timestep_end
  # [../]
  # [./dc4]
  #   type = DeltaUAux
  #   variable = delta_c4
  #   coupled_variable = c4    
  #   execute_on = timestep_end
  # [../]
#   [./dc]
#     type = DeltaUAux
#     variable = delta_c
#     coupled_variable = c    
#     execute_on = timestep_end
#   [../]
  [Fglobal_total]
    type = KKSMultiFreeEnergy
    Fj_names = 'f1 f2 f3 f4'
    hj_names = 'h1 h2 h3 h4'
    gj_names = 'g1 g2 g3 g4'
    variable = Fglobal
    w = 0.2
    interfacial_vars = 'eta1  eta2 eta3 eta4'
    kappa_names      = 'kappa kappa kappa kappa'
  []
  # [./pot]
  #   type = DeltaUAux
  #   variable = delta_pot
  #   coupled_variable = pot    
  #   execute_on = timestep_end
  # [../]

  # [c_mix_calc]
  #   type = ParsedAux
  #   variable = c_mix
  #   coupled_variables = 'c1 c2 c3 c4 eta1 eta2 eta3 eta4'
  #   constant_names = 'a b'
  #   constant_expressions = '10 15'
  #   expression = 'c1*eta1^3*(a-b*eta1+6*eta1^2)+c2*eta2^3*(a-b*eta2+6*eta2^2)+c3*eta3^3*(a-b*eta3+6*eta3^2)+c4*eta4^3*(a-b*eta4+6*eta4^2)'
  #   execute_on = TIMESTEP_END
  # []
  [eta_sum_calc]
    type = ParsedAux
    variable = eta_sum
    coupled_variables = 'eta1 eta2 eta3 eta4'
    expression = 'eta1+eta2+eta3+eta4'
    execute_on = TIMESTEP_END
  []
[]

[Executioner]
  type = Transient
  solve_type = 'NEWTON'
  
  petsc_options_iname = '-ksp_type -pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'preonly   lu        mumps'
  
  dtmax = 1e2
  end_time = 1e7
  l_tol = 1e-3
  nl_max_its = 30
  nl_rel_tol = 1e-6
  nl_abs_tol = 1e-7
  line_search = basic
  [./TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-3
    growth_factor = 1.1
  [../]
  
  # [./Adaptivity]
  #   interval = 5
  #   initial_adaptivity = 4
  #   refine_fraction = 0.8
  #   coarsen_fraction = 0.1
  #   max_h_level = 2
  # [../]
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
  [./eta1_min]
    type = NodalExtremeValue
    variable = eta1
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./eta1_max]
    type = NodalExtremeValue
    variable = eta1
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  # [./c1_min]
  #   type = NodalExtremeValue
  #   variable = c1
  #   value_type = min
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  # [./c1_max]
  #   type = NodalExtremeValue
  #   variable = c1
  #   value_type = max
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  [./eta2_min]
    type = NodalExtremeValue
    variable = eta2
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./eta2_max]
    type = NodalExtremeValue
    variable = eta2
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  # [./c2_min]
  #   type = NodalExtremeValue
  #   variable = c2
  #   value_type = min
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  # [./c2_max]
  #   type = NodalExtremeValue
  #   variable = c2
  #   value_type = max
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  [./eta3_min]
    type = NodalExtremeValue
    variable = eta3
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./eta3_max]
    type = NodalExtremeValue
    variable = eta3
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  # [./c3_min]
  #   type = NodalExtremeValue
  #   variable = c3
  #   value_type = min
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  # [./c3_max]
  #   type = NodalExtremeValue
  #   variable = c3
  #   value_type = max
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  [./eta4_min]
    type = NodalExtremeValue
    variable = eta4
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  [./eta4_max]
    type = NodalExtremeValue
    variable = eta4
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  [../]
  # [./c4_min]
  #   type = NodalExtremeValue
  #   variable = c4
  #   value_type = min
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  # [./c4_max]
  #   type = NodalExtremeValue
  #   variable = c4
  #   value_type = max
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  # [./pot_min]
  #   type = NodalExtremeValue
  #   variable = pot
  #   value_type = min
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
  # [./pot_max]
  #   type = NodalExtremeValue
  #   variable = pot
  #   value_type = max
  #   execute_on = 'INITIAL TIMESTEP_END'
  # [../]
[]

[Outputs]
  exodus = true
  time_step_interval = 1
  file_base = results/solid1/LiSingle
  csv=true
[]
