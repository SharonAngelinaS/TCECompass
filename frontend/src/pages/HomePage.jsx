import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar"; // Import the Navbar component
import "../styles/HomePage.css";
import "../styles/DescriptionModal.css"; // Import the modal styles

const departments = [
  "CSBS",
  "IT",
  "Computer Science",
  "Data Science",
  "EEE",
  "ECE",
  "Civil",
  "Mechatronics",
  "Mechanical",
  "Mathematics",
  "English",
  "Physics",
  "Chemistry",
];

const HomePage = () => {
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleModalToggle = () => {
    setIsModalOpen(!isModalOpen);
  };

  return (
    <>
      <Navbar />
      <div className="home-container">
        <div className="home-toolbar">
          <button type="button" className="description-button" onClick={handleModalToggle}>
            Hall guide
          </button>
        </div>
        <div className="home-main">
          <h1 className="home-heading">Choose a department</h1>
          <div className="cards-container">
            {departments.map((department) => (
              <div
                key={department}
                className="department-card"
                onClick={() => navigate(`/floor/${department}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    navigate(`/floor/${department}`);
                  }
                }}
              >
                <h3>{department}</h3>
              </div>
            ))}
          </div>
        </div>
        {isModalOpen && (
          <div className="modal-overlay" onClick={handleModalToggle}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h2>Department Hall Details</h2>
              <p>A halls - ECE dept</p>
              <p>B halls - Mechatronics dept</p>
              <p>C halls - Civil dept</p>
              <p>M halls - Mechanical dept</p>
              <p>ITT halls - CSBS dept</p>
              <p>IG, IF, IS - IT dept, CSE dept</p>
              <p>IG, LR - Data Science Dept</p>
              <button className="close-modal" onClick={handleModalToggle}>
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default HomePage;
