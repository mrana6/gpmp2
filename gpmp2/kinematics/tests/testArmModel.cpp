/**
*  @file testArmModel.cpp
*  @author Jing Dong
*  @date Dec 30, 2015
**/

#include <CppUnitLite/TestHarness.h>

#include <gtsam/base/Testable.h>
#include <gtsam/base/numericalDerivative.h>

#include <gpmp2/kinematics/ArmModel.h>

#include <iostream>

using namespace std;
using namespace gpmp2;


// sph pos wrapper
gtsam::Point3 sph_pos_wrapper_batch(const ArmModel& arm, const gtsam::Vector& jp, size_t i) {
  vector<gtsam::Point3, Eigen::aligned_allocator<gtsam::Point3>> pos;
  arm.sphereCenters(jp, pos);
  return pos[i];
}

gtsam::Point3 sph_pos_wrapper_single(const ArmModel& arm, const gtsam::Vector& jp, size_t i) {
  return arm.sphereCenter(i, jp);
}

/* ************************************************************************** */
TEST(ArmModel, 2linkPlanarExamples) {

  // 2 link simple example, with none zero base poses
  gtsam::Vector2 a(1, 1), alpha(0, 0), d(0, 0);
  gtsam::Pose3 base_pose(gtsam::Rot3(), gtsam::Point3(2.0, 1.0, -1.0));
  Arm abs_arm(2, a, alpha, d, base_pose);
  gtsam::Vector2 q;

  vector<gtsam::Point3, Eigen::aligned_allocator<gtsam::Point3>> sph_centers_exp, sph_centers_act;
  vector<gtsam::Matrix> J_center_q_act;
  gtsam::Matrix Jcq_exp, Jcq_act;

  // body spheres
  BodySphereVector body_spheres;
  body_spheres.push_back(BodySphere(0, 0.5, gtsam::Point3(-1.0, 0, 0)));
  body_spheres.push_back(BodySphere(0, 0.1, gtsam::Point3(-0.5, 0, 0)));
  body_spheres.push_back(BodySphere(0, 0.1, gtsam::Point3(0, 0, 0)));
  body_spheres.push_back(BodySphere(1, 0.1, gtsam::Point3(-0.5, 0, 0)));
  body_spheres.push_back(BodySphere(1, 0.1, gtsam::Point3(0, 0, 0)));
  const size_t nr_sph = body_spheres.size();

  ArmModel arm(abs_arm, body_spheres);

  // at origin
  q = gtsam::Vector2(0.0, 0.0);
  sph_centers_exp.clear();
  sph_centers_exp.push_back(gtsam::Point3(2, 1, -1));
  sph_centers_exp.push_back(gtsam::Point3(2.5, 1, -1));
  sph_centers_exp.push_back(gtsam::Point3(3, 1, -1));
  sph_centers_exp.push_back(gtsam::Point3(3.5, 1, -1));
  sph_centers_exp.push_back(gtsam::Point3(4, 1, -1));

  arm.sphereCenters(q, sph_centers_act, J_center_q_act);

  for (size_t i = 0; i < nr_sph; i++) {
    EXPECT(assert_equal(sph_centers_exp[i], sph_centers_act[i]));
    Jcq_exp = gtsam::numericalDerivative11(boost::function<gtsam::Point3(const gtsam::Vector2&)>(
          boost::bind(&sph_pos_wrapper_batch, arm, _1, i)), q, 1e-6);
    EXPECT(gtsam::assert_equal(Jcq_exp, J_center_q_act[i], 1e-9));
    EXPECT(assert_equal(sph_centers_exp[i], arm.sphereCenter(i, q, Jcq_act)));
    Jcq_exp = gtsam::numericalDerivative11(boost::function<gtsam::Point3(const gtsam::Vector2&)>(
          boost::bind(&sph_pos_wrapper_single, arm, _1, i)), q, 1e-6);
    EXPECT(gtsam::assert_equal(Jcq_exp, Jcq_act, 1e-9));
  }

  // at non-origin
  q = gtsam::Vector2(M_PI/4.0, M_PI/4.0);
  sph_centers_exp.clear();
  sph_centers_exp.push_back(gtsam::Point3(2, 1, -1));
  sph_centers_exp.push_back(gtsam::Point3(2.353553390593274, 1.353553390593274, -1));
  sph_centers_exp.push_back(gtsam::Point3(2.707106781186548, 1.707106781186548, -1));
  sph_centers_exp.push_back(gtsam::Point3(2.707106781186548, 2.207106781186548, -1));
  sph_centers_exp.push_back(gtsam::Point3(2.707106781186548, 2.707106781186548, -1));

  arm.sphereCenters(q, sph_centers_act, J_center_q_act);

  for (size_t i = 0; i < nr_sph; i++) {
    EXPECT(gtsam::assert_equal(sph_centers_exp[i], sph_centers_act[i]));
    Jcq_exp = gtsam::numericalDerivative11(boost::function<gtsam::Point3(const gtsam::Vector2&)>(
          boost::bind(&sph_pos_wrapper_batch, arm, _1, i)), q, 1e-6);
    EXPECT(gtsam::assert_equal(Jcq_exp, J_center_q_act[i], 1e-9));
    EXPECT(gtsam::assert_equal(sph_centers_exp[i], arm.sphereCenter(i, q, Jcq_act)));
    Jcq_exp = gtsam::numericalDerivative11(boost::function<gtsam::Point3(const gtsam::Vector2&)>(
          boost::bind(&sph_pos_wrapper_single, arm, _1, i)), q, 1e-6);
    EXPECT(gtsam::assert_equal(Jcq_exp, Jcq_act, 1e-9));
  }
}


/* ************************************************************************** */
/* main function */
int main() {
  TestResult tr;
  return TestRegistry::runAllTests(tr);
}
