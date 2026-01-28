import styled from 'styled-components';

const RippleLoader = () => {
  return (
    <StyledWrapper>
      <div className="loader">
        <div className="text">
          <div className="ball" />
        </div>
        <span><i /></span>
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  .loader {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .loader span {
    position: relative;
    width: 200px;
    height: 200px;
    background-color: #eaeef0;
    border: 6px solid #eaeef0;
    box-shadow:
      -8px -8px 15px rgba(255, 255, 255, 1),
      8px 8px 25px rgba(0, 0, 0, 0.15);
    border-radius: 50%;
    overflow: hidden;
  }

  .loader span:before {
    content: "WC3";
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    color: #bbb9b9;
    letter-spacing: 3px;
    font-size: 23px;
    position: absolute;
    inset: 40px;
    background-color: #eaeef0;
    box-shadow:
      -8px -8px 25px rgba(255, 255, 255, 1),
      8px 8px 25px rgba(0, 0, 0, 0.15),
      inset 3px 3px 10px rgba(0, 0, 0, 0.1),
      inset -1px -1px 15px rgba(255, 255, 255, 1);
    border: 2px solid #eaeef0;
    border-radius: 50%;
    z-index: 1;
  }

  .loader span i {
    position: absolute;
    inset: 0;
    background: linear-gradient(#42abff, #ff4f8b, #ffeb4b);
    border-radius: 50%;
    filter: blur(5px);
    animation: animate 1s linear infinite;
  }

  @keyframes animate {
    0% {
      transform: rotate(0deg);
    }

    100% {
      transform: rotate(360deg);
    }
  }

  .text {
    position: absolute;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    animation: animateText 6s linear infinite;
  }

  @keyframes animateText {
    0% {
      transform: rotate(360deg);
    }

    100% {
      transform: rotate(0deg);
    }
  }

  .ball {
    width: 35px;
    height: 35px;
    background: linear-gradient(#42abff, #ff4f8b, #ffeb4b);
    border: 3px solid #dfdfdf;
    border-radius: 50%;
    box-shadow:
      -8px -8px 15px rgba(255, 255, 255, 1),
      8px 8px 25px rgba(0, 0, 0, 0.15);
    animation: rotate 3s infinite linear;
  }`;

export default RippleLoader;
